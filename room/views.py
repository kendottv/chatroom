from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Sum
from .models import CustomUser, ExamQuestion, ExamPaper, InteractionLog, StudentExamHistory, ExamAnswer, ExamRecord
from .forms import CustomLoginForm, CustomUserCreationForm, AvatarUpdateForm
import bleach
from django.utils.html import strip_tags
import re
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import traceback
from gemini_api.gemini import GeminiAPIWrapper
from asgiref.sync import sync_to_async
from django.template.response import TemplateResponse

def home(request):
    return render(request, 'home.html')  # 首頁

def exam(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    
    current_time = timezone.now()
    
    if request.method == 'POST':
        # 處理 AI 提問
        if request.POST.get('action') == 'ai_question':
            try:
                prompt = request.POST.get('prompt')
                paper_id = request.POST.get('paper_id')
                
                if not prompt:
                    return JsonResponse({'error': '請提供問題'}, status=400)
                
                if paper_id:
                    try:
                        exam_paper = ExamPaper.objects.get(id=paper_id)
                        session_key = f'ai_remaining_{paper_id}'
                        remaining = request.session.get(session_key, sum(q.ai_limit for q in exam_paper.questions.all()))
                        
                        if remaining <= 0:
                            return JsonResponse({'response': '已達 AI 提問上限！', 'remaining': 0}, status=403)
                        
                        # 這裡替換成您的實際 AI 呼叫邏輯，例如使用 Grok 或 OpenAI API
                        response = "這是 AI 的模擬回應..."  # 請替換
                        
                        remaining -= 1
                        request.session[session_key] = remaining
                        
                        InteractionLog.objects.create(
                            user=request.user,
                            question=prompt,
                            response=response,
                            exam_paper=exam_paper,
                            score=0
                        )
                        
                        return JsonResponse({'response': response, 'remaining': remaining})
                    except ExamPaper.DoesNotExist:
                        return JsonResponse({'error': '考卷不存在'}, status=404)
                else:
                    return JsonResponse({'response': '無進行中考試，無法提問', 'remaining': 0}, status=403)
            
            except Exception as e:
                return JsonResponse({'error': f'發生錯誤：{str(e)}'}, status=500)
        
        # 處理結束考試
        if 'end_exam' in request.POST and request.user.is_staff:
            paper_id = request.POST.get('paper_id')
            if paper_id:
                try:
                    exam_paper = ExamPaper.objects.get(id=paper_id)
                    exam_paper.end_time = current_time
                    exam_paper.save()
                    messages.success(request, f"考卷 '{exam_paper.title}' 已結束！")
                    return redirect('room:exam')
                except ExamPaper.DoesNotExist:
                    messages.error(request, "考卷不存在。")
            else:
                messages.error(request, "未提供考卷 ID。")
        
        # 處理考試提交
        elif 'paper_id' in request.POST:
            paper_id = request.POST.get('paper_id')
            if paper_id:
                try:
                    exam_paper = ExamPaper.objects.get(id=paper_id)
                    if current_time < exam_paper.start_time or current_time > exam_paper.end_time:
                        messages.error(request, "考試時間已過或尚未開始。")
                        return redirect('room:exam')

                    student = request.user
                    answers_str = request.POST.get('answers', '{}')
                    print(f"Received answers string: {answers_str}")  # 調試
                    try:
                        answers = json.loads(answers_str) if answers_str else {}
                        print(f"Parsed answers: {answers}")  # 調試
                    except json.JSONDecodeError as e:
                        answers = {}
                        print(f"JSON decode error: {e}")

                    exam_record, created = ExamRecord.objects.update_or_create(
                        student=student,
                        exam_paper=exam_paper,
                        defaults={'submitted_at': current_time, 'is_completed': True}
                    )

                    total_score = 0
                    questions = exam_paper.questions.all()
                    for question in questions:
                        question_id = str(question.id)
                        student_answer = answers.get(question_id)
                        is_correct = False

                        if student_answer is None or (isinstance(student_answer, list) and not any(student_answer)):
                            student_answer = None
                        elif isinstance(student_answer, str) and not student_answer.strip():
                            student_answer = ''  

                        print(f"Processing question {question_id}: student_answer = {student_answer}")  # 調試

                        if student_answer is not None:
                            if question.question_type == 'sc':
                                try:
                                    user_option_index = int(student_answer) if isinstance(student_answer, (str, int)) else None
                                    correct_option_index = int(question.correct_option_indices) if question.correct_option_indices else None
                                    is_correct = user_option_index == correct_option_index
                                except (ValueError, TypeError):
                                    is_correct = False
                            elif question.question_type == 'mcq':
                                try:
                                    user_options = sorted(map(str, student_answer)) if isinstance(student_answer, list) else sorted(student_answer.split(',')) if student_answer else []
                                    correct_options = sorted(question.correct_option_indices.split(',')) if question.correct_option_indices else []
                                    is_correct = user_options == correct_options
                                except Exception as e:
                                    print(f"MCQ error: {e}")
                                    is_correct = False
                            elif question.question_type == 'tf':
                                student_bool = str(student_answer).lower() in ['true', '1', 't', 'yes', 'y', '是', '對', '正確']
                                is_correct = student_bool == question.is_correct
                            elif question.question_type in ['sa', 'essay']:
                                is_correct = str(student_answer).strip().lower() == str(question.correct_option_indices).strip().lower() if question.correct_option_indices else False

                            score = question.points if is_correct else 0
                            total_score += score
                        else:
                            score = 0

                        ExamAnswer.objects.update_or_create(
                            exam_record=exam_record,
                            exam_question=question,
                            defaults={
                                'student_answer': student_answer,
                                'score': score,
                                'is_correct': is_correct
                            }
                        )

                        InteractionLog.objects.create(
                            user=student,
                            question=f"題目: {question.title or question.content[:50]}..., 回答: {student_answer if student_answer is not None else '未作答'}",
                            response=f"回答 {'正確' if is_correct else '錯誤' if question.correct_option_indices or question.is_correct else '已記錄'}, 得分: {score}/{question.points}",
                            exam_question=question,
                            exam_paper=exam_paper,
                            score=score
                        )

                    StudentExamHistory.objects.update_or_create(
                        student=student,
                        exam_paper=exam_paper,
                        defaults={
                            'total_score': total_score,
                            'completed_at': current_time,
                            'grade': 'A' if total_score >= 90 else 'B' if total_score >= 80 else 'C'
                        }
                    )

                    exam_record.score = total_score
                    exam_record.save()
                    messages.success(request, f"考試 '{exam_paper.title}' 已提交，總分 {total_score} / {exam_paper.total_points} 分！")
                    return redirect('room:exam')

                except ExamPaper.DoesNotExist:
                    messages.error(request, "考卷不存在。")
                except Exception as e:
                    messages.error(request, f"提交過程中發生錯誤：{str(e)}")
                    print(f"Exception in exam submission: {e}")

    # GET 請求的處理
    all_papers = ExamPaper.objects.all().prefetch_related('questions')
    exam_records = ExamRecord.objects.filter(student=request.user).values('exam_paper_id', 'is_completed')
    exam_records_dict = {record['exam_paper_id']: {'is_completed': record['is_completed']} for record in exam_records}

    available_papers = [
        paper for paper in all_papers
        if paper.publish_time <= current_time and paper.end_time > current_time and
        not exam_records_dict.get(paper.id, {}).get('is_completed', False)
    ]
    
    # 計算 AI 提問次數並初始化 session
    for paper in available_papers:
        paper.ai_total_limit = sum(q.ai_limit for q in paper.questions.all())
        session_key = f'ai_remaining_{paper.id}'
        if session_key not in request.session:
            request.session[session_key] = paper.ai_total_limit
        paper.ai_remaining = request.session[session_key]

    student_answers = {}
    
    if available_papers:
        paper_ids = [paper.id for paper in available_papers]
        saved_answers = ExamAnswer.objects.filter(
            exam_record__student=request.user,
            exam_record__exam_paper_id__in=paper_ids,
            exam_record__is_completed=False
        ).select_related('exam_record', 'exam_question')
        
        for answer in saved_answers:
            paper_id = answer.exam_record.exam_paper_id
            question_id = answer.exam_question.id
            if paper_id not in student_answers:
                student_answers[paper_id] = {}
            student_answers[paper_id][question_id] = answer.student_answer or ""
    
    for paper in available_papers:
        paper.questions_with_answers = []
        paper_answers = student_answers.get(paper.id, {})
        
        for question in paper.questions.all():
            question.student_answer = paper_answers.get(question.id, "")
            if question.question_type == 'mcq' and question.student_answer:
                if isinstance(question.student_answer, str):
                    question.student_answer_list = question.student_answer.split(',')
                else:
                    question.student_answer_list = question.student_answer if isinstance(question.student_answer, list) else []
            else:
                question.student_answer_list = []
            
            paper.questions_with_answers.append(question)
    
    if not available_papers:
        messages.info(request, "目前沒有進行中的考試。請聯繫管理員或檢查時間設置。")
        context = {
            'exam_papers': [],
            'exam_records': exam_records_dict,
            'user': request.user,
            'ai_total_limit': 0,
            'ai_remaining': 0,
        }
    else:
        context = {
            'exam_papers': available_papers,
            'exam_records': exam_records_dict,
            'user': request.user,
            'ai_total_limit': available_papers[0].ai_total_limit,
            'ai_remaining': available_papers[0].ai_remaining,
        }
    
    return render(request, 'exam.html', context)


@login_required
def select_exam(request):
    current_time = timezone.now()

    all_papers = ExamPaper.objects.all().prefetch_related('questions')
    exam_records = ExamRecord.objects.filter(student=request.user).values('exam_paper_id', 'is_completed')
    exam_records_dict = {r['exam_paper_id']: {'is_completed': r['is_completed']} for r in exam_records}

    available_papers = [
        p for p in all_papers
        if p.publish_time <= current_time < p.end_time
        and not exam_records_dict.get(p.id, {}).get('is_completed', False)
    ]

    if request.method == 'POST':
        exam_paper_id = request.POST.get('exam_paper')
        if not exam_paper_id:
            messages.error(request, "請選擇一張考卷。")
            return redirect('room:select_exam')

        try:
            exam_paper = ExamPaper.objects.get(id=exam_paper_id)
        except ExamPaper.DoesNotExist:
            messages.error(request, "選擇的考卷不存在。")
            return redirect('room:select_exam')

        # 時間與已完成檢查
        if not (exam_paper.publish_time <= current_time < exam_paper.end_time):
            messages.error(request, "此考卷目前不可作答（尚未開始或已結束）。")
            return redirect('room:select_exam')

        already_done = ExamRecord.objects.filter(
            student=request.user, exam_paper=exam_paper, is_completed=True
        ).exists()
        if already_done:
            messages.info(request, "此考卷您已經完成。")
            return redirect('room:select_exam')

        # OK：存入 session 並前往作答
        request.session['selected_exam_paper_id'] = str(exam_paper.id)
        return redirect('room:exam')

    return render(request, 'select_exam.html', {'available_papers': available_papers})

@login_required
def teacher_exam(request):
    """
    處理教師出題頁面，包括新增/編輯題目、題目庫管理、創建/編輯考試。
    僅限授權教師訪問。
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "您無權限訪問此頁面。")
        return render(request, 'teacher_exam.html')

    now = timezone.now()

    # 題庫：全部撈出（你可改成 filter(created_by=request.user)）
    all_questions = ExamQuestion.objects.all().order_by('-id')

    # 統一準備模板會用到的屬性
    for q in all_questions:
        # options 轉為 list（若為 None 則給空 list）
        try:
            q.options = list(q.options) if q.options else []
        except Exception:
            q.options = []
        # 多選正確索引列表（模板用 question.correct_option_indices_list）
        q.correct_option_indices_list = []
        if q.correct_option_indices:
            raw = str(q.correct_option_indices)
            if ',' in raw:
                try:
                    q.correct_option_indices_list = [int(x) for x in raw.split(',') if x.strip() != '']
                except Exception:
                    q.correct_option_indices_list = []
            else:
                try:
                    q.correct_option_indices_list = [int(raw)]
                except Exception:
                    q.correct_option_indices_list = []

    # 考卷列表：顯示自己的全部考卷（含已結束），交給模板以 is_open 控制
    exam_papers = (ExamPaper.objects
                   .filter(created_by=request.user)
                   .order_by('-id')
                   .prefetch_related('questions'))
    for p in exam_papers:
        p.is_open = (p.end_time > now)

    question_types = {'sc': '單選題', 'mcq': '多選題', 'tf': '是非題', 'sa': '簡答題'}
    question_to_edit = None
    exam_to_edit = None
    initial_question_ids_json = '[]'

    if request.method == 'POST':
        # ----- 新增 / 編輯題目 -----
        if 'question_text' in request.POST:
            question_id = request.POST.get('question_id')
            title = request.POST.get('title', '無題目標題').strip()
            ai_limit = request.POST.get('ai_limit', '1').strip()
            raw_content = request.POST.get('question_text', '').strip()

            if not raw_content or raw_content == '<p><br></p>':
                messages.error(request, "題目內容不能為空。")
                return render(request, 'teacher_exam.html', {
                    'all_questions': all_questions,
                    'question_to_edit': question_to_edit,
                    'question_types': question_types,
                    'exam_papers': exam_papers,
                    'exam_to_edit': exam_to_edit,
                    'now': now,
                    'initial_question_ids_json': initial_question_ids_json,
                })

            # 僅保留段落 p（可依需求放寬）
            content = bleach.clean(raw_content, tags=['p', 'b', 'i', 'u', 'ol', 'ul', 'li', 'br', 'strong', 'em'], strip=True)
            if not content.startswith('<p>'):
                content = f'<p>{content}</p>'

            question_type = request.POST.get('question_type', 'sa')

            options = []
            if question_type in ['sc', 'mcq']:
                for i in range(1, 5):
                    option_value = request.POST.get(f'option_{i}', '').strip()
                    if option_value:
                        options.append(option_value)
                if not options:
                    messages.error(request, "請至少填寫一個選項。")
                    return render(request, 'teacher_exam.html', {
                        'all_questions': all_questions,
                        'question_to_edit': question_to_edit,
                        'question_types': question_types,
                        'exam_papers': exam_papers,
                        'exam_to_edit': exam_to_edit,
                        'now': now,
                        'initial_question_ids_json': initial_question_ids_json,
                    })

            is_correct = None
            correct_option_indices = None

            if question_type == 'sc':
                correct_option = request.POST.get('correct_option')
                if correct_option is not None:
                    try:
                        idx = int(correct_option)
                        if 0 <= idx < len(options):
                            correct_option_indices = str(idx)
                    except (ValueError, TypeError):
                        messages.error(request, "無效的正確選項索引。")
                        return render(request, 'teacher_exam.html', {
                            'all_questions': all_questions,
                            'question_to_edit': question_to_edit,
                            'question_types': question_types,
                            'exam_papers': exam_papers,
                            'exam_to_edit': exam_to_edit,
                            'now': now,
                            'initial_question_ids_json': initial_question_ids_json,
                        })

            elif question_type == 'mcq':
                correct_options = request.POST.getlist('correct_options')
                if correct_options:
                    try:
                        valid_options = [str(idx) for idx in map(int, correct_options) if 0 <= idx < len(options)]
                    except Exception:
                        valid_options = []
                    if valid_options:
                        correct_option_indices = ','.join(sorted(valid_options))

            elif question_type == 'tf':
                tf_answer = request.POST.get('correct_answer', '').strip().lower()
                if tf_answer in ['true', '1', 't', 'yes', 'y', '是', '對', '正確']:
                    is_correct = True
                elif tf_answer in ['false', '0', 'f', 'no', 'n', '否', '錯', '錯誤']:
                    is_correct = False
                else:
                    messages.error(request, "請選擇真或假作為正確答案。")
                    return render(request, 'teacher_exam.html', {
                        'all_questions': all_questions,
                        'question_to_edit': question_to_edit,
                        'question_types': question_types,
                        'exam_papers': exam_papers,
                        'exam_to_edit': exam_to_edit,
                        'now': now,
                        'initial_question_ids_json': initial_question_ids_json,
                    })

            else:  # sa
                # ✅ 修正：簡答題從 sa_answer 讀值（原本讀 correct_answer 會拿不到）
                sa_answer = request.POST.get('sa_answer', '').strip()
                correct_option_indices = sa_answer if sa_answer else None

            try:
                points = int(request.POST.get('points', 10))
                ai_limit = int(ai_limit)
                if points < 0 or points > 100 or ai_limit < 1:
                    raise ValueError("無效的配分或 AI 問答次數限制")
            except (ValueError, TypeError) as e:
                messages.error(request, f"無效的配分或 AI 問答次數限制：{str(e)}")
                return render(request, 'teacher_exam.html', {
                    'all_questions': all_questions,
                    'question_to_edit': question_to_edit,
                    'question_types': question_types,
                    'exam_papers': exam_papers,
                    'exam_to_edit': exam_to_edit,
                    'now': now,
                    'initial_question_ids_json': initial_question_ids_json,
                })

            image = request.FILES.get('image') if 'image' in request.FILES else None

            try:
                if question_id:
                    exam_question = get_object_or_404(ExamQuestion, id=question_id, created_by=request.user)
                    exam_question.title = title
                    exam_question.content = content
                    exam_question.question_type = question_type
                    exam_question.options = options if options else None
                    exam_question.is_correct = is_correct
                    exam_question.correct_option_indices = correct_option_indices
                    exam_question.points = points
                    exam_question.ai_limit = ai_limit
                    if image:
                        exam_question.image = image
                    exam_question.save()
                    messages.success(request, f"題目 '{title}' 已成功更新！")
                else:
                    exam_question = ExamQuestion.objects.create(
                        title=title,
                        content=content,
                        question_type=question_type,
                        options=options if options else None,
                        is_correct=is_correct,
                        correct_option_indices=correct_option_indices,
                        points=points,
                        ai_limit=ai_limit,
                        created_by=request.user,
                        image=image
                    )
                    InteractionLog.objects.create(
                        user=request.user,
                        question=f"題目: {title}, AI 次數限制: {ai_limit}",
                        response="題目已成功創建",
                        exam_question=exam_question,
                        exam_paper=None
                    )
                    messages.success(request, f"題目 '{title}' 已成功創建！")
            except IntegrityError:
                messages.error(request, "資料庫錯誤，請確保所有字段有效。")
            except Exception as e:
                messages.error(request, f"創建/更新失敗：{str(e)}")

        # ----- 創建考試 -----
        elif request.POST.get('action') == 'create_exam':
            exam_title = request.POST.get('exam_title', '').strip()
            selected_questions_str = request.POST.get('selected_questions', '').strip()

            if not selected_questions_str:
                messages.error(request, "請選擇至少一個題目。")
            else:
                try:
                    question_ids = [int(qid) for qid in selected_questions_str.split(',') if qid.strip()]
                    valid_questions = ExamQuestion.objects.filter(id__in=question_ids)
                    if not valid_questions.exists():
                        messages.error(request, f"所選題目無效。")
                    else:
                        total_points = sum(q.points for q in valid_questions)
                        tz = timezone.get_current_timezone()
                        publish_time = timezone.datetime.strptime(
                            request.POST.get('publish_time', timezone.now().strftime('%Y-%m-%dT%H:%M')),
                            '%Y-%m-%dT%H:%M'
                        ).replace(tzinfo=tz)
                        start_time = timezone.datetime.strptime(
                            request.POST.get('start_time', timezone.now().strftime('%Y-%m-%dT%H:%M')),
                            '%Y-%m-%dT%H:%M'
                        ).replace(tzinfo=tz)
                        end_time = timezone.datetime.strptime(
                            request.POST.get('end_time', (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')),
                            '%Y-%m-%dT%H:%M'
                        ).replace(tzinfo=tz)
                        duration_minutes = int(request.POST.get('duration_minutes', 60))

                        if start_time > end_time:
                            messages.error(request, "開始時間不能晚於截止時間。")
                        else:
                            exam_paper = ExamPaper.objects.create(
                                title=exam_title,
                                total_points=total_points,
                                created_by=request.user,
                                publish_time=publish_time,
                                start_time=start_time,
                                end_time=end_time,
                                duration_minutes=duration_minutes,
                                description=request.POST.get('exam_description', '').strip()
                            )
                            exam_paper.questions.set(valid_questions)
                            messages.success(request, f"考卷 '{exam_title}' 已成功創建！")
                except ValueError as e:
                    messages.error(request, f"時間或題目 ID 格式錯誤：{str(e)}")
                except Exception as e:
                    messages.error(request, f"創建考試失敗：{str(e)}")

        # ----- 編輯考試 -----
        elif request.POST.get('action') == 'edit_exam':
            exam_id = request.POST.get('exam_id')
            exam_title = request.POST.get('exam_title', '').strip()
            selected_questions_str = request.POST.get('selected_questions', '').strip()
            try:
                exam_paper = get_object_or_404(ExamPaper, id=exam_id, created_by=request.user)
                tz = timezone.get_current_timezone()
                exam_paper.title = exam_title
                exam_paper.description = request.POST.get('exam_description', '').strip()
                exam_paper.publish_time = timezone.datetime.strptime(
                    request.POST.get('publish_time', timezone.now().strftime('%Y-%m-%dT%H:%M')),
                    '%Y-%m-%dT%H:%M'
                ).replace(tzinfo=tz)
                exam_paper.start_time = timezone.datetime.strptime(
                    request.POST.get('start_time', timezone.now().strftime('%Y-%m-%dT%H:%M')),
                    '%Y-%m-%dT%H:%M'
                ).replace(tzinfo=tz)
                exam_paper.end_time = timezone.datetime.strptime(
                    request.POST.get('end_time', (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')),
                    '%Y-%m-%dT%H:%M'
                ).replace(tzinfo=tz)
                exam_paper.duration_minutes = int(request.POST.get('duration_minutes', 60))

                if exam_paper.start_time > exam_paper.end_time:
                    messages.error(request, "開始時間不能晚於截止時間。")
                else:
                    if selected_questions_str:
                        question_ids = [int(qid) for qid in selected_questions_str.split(',') if qid.strip()]
                        valid_questions = ExamQuestion.objects.filter(id__in=question_ids)
                        if not valid_questions.exists():
                            messages.error(request, "所選題目無效。")
                        else:
                            exam_paper.total_points = sum(q.points for q in valid_questions)
                            exam_paper.questions.set(valid_questions)
                    else:
                        exam_paper.questions.clear()
                        exam_paper.total_points = 0

                    exam_paper.save()
                    messages.success(request, f"考卷 '{exam_title}' 已成功更新！")
            except ValueError as e:
                messages.error(request, f"時間或題目 ID 格式錯誤：{str(e)}")
            except Exception as e:
                messages.error(request, f"編輯考試失敗：{str(e)}")

        # ----- 刪除題目 -----
        elif 'delete_question' in request.POST:
            question_ids = request.POST.getlist('delete_questions')
            if question_ids:
                try:
                    question_ids = [int(qid) for qid in question_ids if qid.strip()]
                    deleted_count, _ = ExamQuestion.objects.filter(
                        id__in=question_ids, created_by=request.user
                    ).delete()
                    if deleted_count > 0:
                        messages.success(request, f"成功刪除 {deleted_count} 個題目！")
                    else:
                        messages.warning(request, "未找到可刪除的題目或無權限。")
                except ValueError:
                    messages.error(request, "題目 ID 格式錯誤。")
            else:
                messages.error(request, "請選擇至少一個題目進行刪除。")

    # GET：處理編輯題目
    edit_id = request.GET.get('edit')
    if edit_id:
        question_to_edit = get_object_or_404(ExamQuestion, id=edit_id, created_by=request.user)
        if question_to_edit.options is None:
            question_to_edit.options = ['', '', '', '']
        while len(question_to_edit.options) < 4:
            question_to_edit.options.append('')
        if question_to_edit.content is None:
            question_to_edit.content = ''
        if question_to_edit.question_type == 'mcq' and question_to_edit.correct_option_indices:
            try:
                question_to_edit.correct_answer_list = question_to_edit.correct_option_indices.split(',')
            except Exception:
                question_to_edit.correct_answer_list = []
        elif question_to_edit.question_type == 'sc' and question_to_edit.correct_option_indices:
            question_to_edit.correct_answer_list = [question_to_edit.correct_option_indices]
        else:
            question_to_edit.correct_answer_list = []

    # GET：處理編輯考卷
    edit_exam_id = request.GET.get('edit_exam')
    if edit_exam_id:
        exam_to_edit = get_object_or_404(ExamPaper, id=edit_exam_id, created_by=request.user)
        initial_ids = list(exam_to_edit.questions.values_list('id', flat=True))
        initial_question_ids_json = json.dumps(initial_ids)

    return render(request, 'teacher_exam.html', {
        'all_questions': all_questions,
        'question_to_edit': question_to_edit,
        'question_types': question_types,
        'exam_papers': exam_papers,
        'exam_to_edit': exam_to_edit,
        'now': now,
        'initial_question_ids_json': initial_question_ids_json,
    })

@login_required
def student_exam_history(request):
    """
    顯示每個學生的每個考試的每個題目答題紀錄。
    僅限已認證且具有管理權限的用戶訪問。
    """
    if not request.user.is_staff:
        messages.error(request, "您無權限訪問此頁面。")
        return redirect('room:teacher_exam')

    # 獲取所有學生的考試歷史
    histories = StudentExamHistory.objects.all().order_by('-completed_at')
    User = get_user_model()  # 獲取 CustomUser 模型
    detailed_records = []

    for history in histories:
        exam_record = ExamRecord.objects.filter(
            student=history.student,
            exam_paper=history.exam_paper
        ).first()
        
        if exam_record:
            exam_answers = exam_record.answer_details.all()
            questions_with_answers = []
            for answer in exam_answers:
                question = ExamQuestion.objects.get(id=answer.exam_question.id)
                questions_with_answers.append({
                    'question_title': question.title,
                    'question_content': question.content,
                    'student_answer': answer.student_answer,
                    'score': answer.score,
                    'is_correct': answer.is_correct,
                    'question_type': question.get_question_type_display(),
                    'question_id': question.id,
                    'points': question.points,
                })
            # 使用 get_full_name() 獲取學生姓名
            student_name = history.student.get_full_name() or history.student.username
            
            detailed_records.append({
                'student_id': history.student.student_id,
                'student_name': student_name,  # 使用 get_full_name() 或 username
                'exam_title': history.exam_paper.title,
                'total_score': history.total_score,
                'completed_at': history.completed_at,
                'answers': questions_with_answers,
            })

    if request.method == 'POST' and 'update_scores' in request.POST:
        try:
            student_exam_key = request.POST['update_scores'].split('_')
            student_id = student_exam_key[0]
            exam_title = '_'.join(student_exam_key[1:])
            history = StudentExamHistory.objects.filter(
                student__student_id=student_id,
                exam_paper__title=exam_title
            ).first()

            if not history:
                messages.error(request, "找不到對應的考試歷史紀錄。")
                return render(request, 'student_exam_history.html', {'detailed_records': detailed_records})

            exam_record = ExamRecord.objects.filter(
                student=history.student,
                exam_paper=history.exam_paper
            ).first()

            if not exam_record:
                messages.error(request, "找不到對應的考試紀錄。")
                return render(request, 'student_exam_history.html', {'detailed_records': detailed_records})

            total_score = 0
            for answer in exam_record.answer_details.all():
                new_score = request.POST.get(f'score_{answer.exam_question.id}')
                if new_score is not None:
                    try:
                        new_score = int(new_score)
                        max_score = answer.exam_question.points
                        if 0 <= new_score <= max_score:
                            answer.score = new_score
                            answer.is_correct = (new_score == max_score)  # 滿分視為正確
                            answer.save()
                            total_score += new_score
                        else:
                            messages.warning(request, f"題目 ID {answer.exam_question.id} 的調分 {new_score} 超出範圍 (0-{max_score})，未更新。")
                    except ValueError:
                        messages.warning(request, f"題目 ID {answer.exam_question.id} 的調分無效，需為數字。")

            # 更新總分
            history.total_score = total_score
            history.save()
            exam_record.score = total_score
            exam_record.save()
            messages.success(request, f"已成功更新 {student_id} 的 '{exam_title}' 考試成績，總分為 {total_score}。")
            return redirect('room:student_exam_history')

        except (ValueError, CustomUser.DoesNotExist, ExamPaper.DoesNotExist):
            messages.error(request, "更新分數失敗，無效的學生或考卷。")
        except Exception as e:
            messages.error(request, f"更新分數時發生錯誤：{str(e)}")

    return render(request, 'student_exam_history.html', {'detailed_records': detailed_records})

def readme(request):
    return render(request, 'readme.html')  # ReadMe 頁

def history(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    history_records = InteractionLog.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'history.html', {'history_records': history_records})  # 歷史頁

@login_required
def profile(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    
    exam_records = ExamRecord.objects.filter(student=request.user).select_related('exam_paper').order_by('-submitted_at')

    if request.method == 'POST':
        form = AvatarUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "頭像更新成功！")
            return redirect('profile')
    else:
        form = AvatarUpdateForm(instance=request.user)

    return render(request, 'profile.html', {
        'user': request.user,
        'exam_records': exam_records,
        'avatar_form': form
    })

def custom_login(request):
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            messages.success(request, f"歡迎，{user.username}！")
            return redirect('room:home')  # 修正為 room:home
    else:
        form = CustomLoginForm()
    return render(request, 'login.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"註冊成功，歡迎 {user.username}！")
            return redirect('room:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import ExamPaper, InteractionLog

@login_required
@csrf_exempt
@require_POST
async def ask_ai(request):
    prompt = (request.POST.get('prompt') or '').strip()
    if not prompt:
        return HttpResponse("請提供 prompt 內容。", status=400)

    # 確保/更新 session（避免在 async 直接觸發同步 DB）
    async def ensure_session_and_touch():
        if not request.session.session_key:
            await sync_to_async(request.session.save)()
        def _touch():
            request.session['last_seen'] = timezone.now().isoformat()
            request.session.save()
        await sync_to_async(_touch)()
        return request.session.session_key

    session_key = await ensure_session_and_touch()

    # 呼叫 Gemini（你的 wrapper 內部已處理 Redis 與聯網工具）
    wrapper = GeminiAPIWrapper(session_key=session_key)
    answer_text = await wrapper.async_get_response(prompt)

    # 避免觸發 request.user → 直接從 session 取 user_id
    user_id = await sync_to_async(lambda: request.session.get('_auth_user_id'))()
    user_id = int(user_id) if user_id else None

    # ORM 寫入放到 thread
    await sync_to_async(InteractionLog.objects.create)(
        user_id=user_id,
        question=prompt,
        response=answer_text,
    )

    # ⭐ 關鍵修正：模板渲染在 thread 裡完成，避免在 async context 觸發同步 ORM
    resp = TemplateResponse(request, "exam.html", {"response": answer_text})
    await sync_to_async(resp.render)()   # 在 thread 中完成渲染
    return resp

def upload_question(request):
    if request.method == 'POST' and request.user.is_staff:
        title = request.POST.get('title', '無題目標題')
        content = request.POST.get('question', '')
        ai_limit = request.POST.get('ai_limit', 0)  # 新增：AI 問答次數限制
        image = request.FILES.get('image') if 'image' in request.FILES else None
        if content:
            exam_question = ExamQuestion.objects.create(
                title=title,
                content=content,
                ai_limit=ai_limit,  # 新增：儲存 ai_limit
                created_by=request.user,
                image=image
            )
            InteractionLog.objects.create(
                user=request.user,
                question=f"題目: {content}, AI 次數限制: {ai_limit}",
                response="題目已成功創建",
                exam_question=exam_question,
                exam_paper=None
            )
            return HttpResponse(f"題目 '{title}' 已上傳，AI 問答次數限制: {ai_limit}")
    return HttpResponse("無權限或請使用 POST 方法提交題目。")

def ask_exam_question(request):
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        answer = request.POST.get('answer', '').strip()
        if question_id:
            try:
                exam_question = ExamQuestion.objects.get(id=question_id)
                is_correct = False
                if exam_question.question_type == 'mcq':
                    try:
                        user_options = sorted(map(str, answer)) if isinstance(answer, (list, tuple)) else sorted(answer.split(',')) if answer else []
                        correct_options = sorted(exam_question.correct_option_indices.split(',')) if exam_question.correct_option_indices else []
                        is_correct = user_options == correct_options
                    except:
                        is_correct = False
                elif exam_question.question_type == 'tf':
                    user_bool = str(answer).lower() in ['true', '1', 't', 'yes', 'y', '是', '對', '正確']
                    is_correct = user_bool == exam_question.is_correct
                elif exam_question.question_type in ['sa', 'essay']:
                    is_correct = str(answer).strip().lower() == str(exam_question.correct_option_indices).strip().lower() if exam_question.correct_option_indices else False

                score = exam_question.points if is_correct else 0
                InteractionLog.objects.create(
                    user=request.user,
                    question=f"題目: {exam_question.title}, 回答: {answer}",
                    response=f"回答 {'正確' if is_correct else '錯誤'}, 得分: {score}",
                    exam_question=exam_question,
                    exam_paper=None
                )
                messages.success(request, f"回答提交成功！得分: {score} / {exam_question.points} 分")
            except ExamQuestion.DoesNotExist:
                messages.error(request, "題目不存在。")
        return redirect('room:exam')
    return HttpResponse("請使用 POST 方法提交回答。")

@login_required
def submit_single_answer(request):
    if request.method == 'POST':
        try:
            # 解析 JSON 數據
            data = json.loads(request.body.decode('utf-8'))
            paper_id = data.get('paper_id')
            question_id = data.get('question_id')
            answer = data.get('answer')

            # 檢查必要參數
            if not all([paper_id, question_id]):
                return JsonResponse({'status': 'error', 'message': '缺少必要參數（考卷 ID 或題目 ID）'}, status=400)

            # 獲取相關物件
            exam_paper = get_object_or_404(ExamPaper, id=paper_id)
            exam_question = get_object_or_404(ExamQuestion, id=question_id)
            exam_record, created = ExamRecord.objects.get_or_create(
                student=request.user,
                exam_paper=exam_paper,
                defaults={'score': 0, 'is_completed': False}
            )

            # 處理 answer，可能為 None、空字符串或空列表
            if answer is None:
                student_answer = None
            elif isinstance(answer, list) and not answer:
                student_answer = []  # 保留空列表以表示未選項
            elif isinstance(answer, str) and not answer.strip():
                student_answer = ""  # 保留空字符串以表示未輸入
            else:
                student_answer = answer

            # 判斷答案是否正確
            is_correct = False
            if exam_question.question_type == 'sc':
                try:
                    user_option = int(student_answer) if student_answer is not None and student_answer != "" else None
                    correct_option = int(exam_question.correct_option_indices) if exam_question.correct_option_indices else None
                    is_correct = user_option == correct_option
                except (ValueError, TypeError):
                    is_correct = False
            elif exam_question.question_type == 'mcq':
                try:
                    user_options = sorted(map(str, student_answer)) if isinstance(student_answer, list) else sorted(student_answer.split(',')) if student_answer else []
                    correct_options = sorted(exam_question.correct_option_indices.split(',')) if exam_question.correct_option_indices else []
                    is_correct = user_options == correct_options
                except:
                    is_correct = False
            elif exam_question.question_type == 'tf':
                user_bool = str(student_answer).lower() in ['true', '1', 't', 'yes', 'y', '是', '對', '正確'] if student_answer else None
                is_correct = user_bool == exam_question.is_correct
            elif exam_question.question_type in ['sa', 'essay']:
                is_correct = str(student_answer).strip().lower() == str(exam_question.correct_option_indices).strip().lower() if student_answer and exam_question.correct_option_indices else False

            # 儲存或更新答題紀錄
            exam_answer, created = ExamAnswer.objects.update_or_create(
                exam_record=exam_record,
                exam_question=exam_question,
                defaults={
                    'student_answer': student_answer,
                    'score': exam_question.points if is_correct else 0,
                    'is_correct': is_correct,
                    'answered_at': timezone.now()
                }
            )

            # 更新總分
            total_score = ExamAnswer.objects.filter(exam_record=exam_record).aggregate(total=Sum('score'))['total'] or 0
            exam_record.score = total_score
            exam_record.save()

            # 記錄互動
            InteractionLog.objects.create(
                user=request.user,
                question=f"題目: {exam_question.title or exam_question.content[:50]}..., 回答: {student_answer if student_answer is not None else '未作答'}",
                response=f"回答 {'正確' if is_correct else '錯誤' if exam_question.correct_option_indices or exam_question.is_correct else '已記錄'}, 得分: {exam_answer.score}/{exam_question.points}",
                exam_question=exam_question,
                exam_paper=exam_paper,
                score=exam_answer.score
            )

            # 更新 StudentExamHistory
            StudentExamHistory.objects.update_or_create(
                student=request.user,
                exam_paper=exam_paper,
                defaults={'total_score': total_score, 'completed_at': timezone.now()}
            )

            return JsonResponse({'status': 'success', 'message': '答案提交成功', 'score': exam_answer.score})
        except ExamPaper.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '考卷不存在'}, status=404)
        except ExamQuestion.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '題目不存在'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': '無效的 JSON 數據'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': '僅接受 POST 請求'}, status=405)

def logout(request):
    auth_logout(request)  # 執行登出
    return redirect('room:home')

def _session_touch(session):
    """同步函式：觸碰 session 並寫入 last_seen。"""
    session["last_seen"] = timezone.now().isoformat()
    session.save()

def _sum_ai_limit_sync(paper_id: int) -> int:
    """同步函式：計算一張考卷的 AI 總額度（各題 ai_limit 加總）。"""
    paper = ExamPaper.objects.get(id=paper_id)
    return sum(q.ai_limit for q in paper.questions.all())

def _consume_once_sync(session, paper_id: int):
    """
    同步函式：從 session 扣 1 次。
    - 首次使用先初始化 total。
    - 回傳 (ok:boolean, remaining:int)。
    """
    key = f"ai_remaining_{paper_id}"
    remaining = session.get(key)
    if remaining is None:
        total = _sum_ai_limit_sync(paper_id)
        session[key] = total
        remaining = total
    if remaining <= 0:
        return False, 0
    session[key] = remaining - 1
    session.modified = True
    return True, remaining - 1

def _rollback_once_sync(session, paper_id: int):
    """同步函式：AI 失敗時把剛扣的 1 次加回去。"""
    key = f"ai_remaining_{paper_id}"
    if key in session:
        session[key] = int(session[key]) + 1
        session.modified = True

@csrf_exempt
@require_POST
async def ai_webhook(request):
    """
    POST /webhooks/ai/
    JSON:
      - 必填:  prompt: str
      - 可選:  paper_id: int（考場情境就帶，會執行扣次並回 remaining）
      - 可選:  session_key: str（外部來源自帶 session）
    回傳:
      - 一般: {"response": "..."}
      - 考場: {"response": "...", "remaining": <int>}
      - 用盡: {"response": "已達 AI 提問上限！", "remaining": 0}  (HTTP 429)
    """
    # 1) 解析 JSON
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    prompt = (payload.get("prompt") or "").strip()
    incoming_session_key = payload.get("session_key")
    paper_id = payload.get("paper_id")  # 可為 None
    if not prompt:
        return JsonResponse({"error": "請提供 prompt"}, status=400)

    # 2) 取得/建立 session_key（包同步操作進 thread）
    async def ensure_session_and_touch():
        if incoming_session_key:
            return incoming_session_key
        if not request.session.session_key:
            await sync_to_async(request.session.save)()
        await sync_to_async(_session_touch)(request.session)
        return request.session.session_key

    session_key = await ensure_session_and_touch()

    # 3) 若有 paper_id → 先檢查考卷存在並先扣 1 次
    remaining = None
    did_decrement = False
    if paper_id is not None:
        try:
            # 確認考卷存在
            await sync_to_async(ExamPaper.objects.get)(id=paper_id)
        except ExamPaper.DoesNotExist:
            return JsonResponse({"error": "考卷不存在"}, status=404)

        ok, remaining = await sync_to_async(_consume_once_sync)(request.session, int(paper_id))
        if not ok:
            return JsonResponse({"response": "已達 AI 提問上限！", "remaining": 0}, status=429)
        did_decrement = True

    # 4) 呼叫 Gemini（失敗就回補額度）
    try:
        wrapper = GeminiAPIWrapper(session_key=session_key)
        answer_text = await wrapper.async_get_response(prompt)
    except Exception as ai_err:
        if did_decrement and paper_id is not None:
            await sync_to_async(_rollback_once_sync)(request.session, int(paper_id))
        return JsonResponse({"error": f"AI 服務錯誤：{ai_err}"}, status=500)

    # 5) 取得 user_id（避免在 async context 直接觸 ORM 或 request.user）
    if incoming_session_key:
        user_id = None
    else:
        user_id = await sync_to_async(lambda: request.session.get("_auth_user_id"))()
        user_id = int(user_id) if user_id else None

    # 6) 記錄互動
    await sync_to_async(InteractionLog.objects.create)(
        user_id=user_id,
        question=prompt,
        response=answer_text,
        exam_paper_id=paper_id if paper_id is not None else None,
    )

    # 7) 回傳 JSON（
    resp = {"response": answer_text}
    if remaining is not None:
        resp["remaining"] = remaining
    return JsonResponse(resp, status=200)