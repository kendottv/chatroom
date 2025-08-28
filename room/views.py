from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.contrib.auth import login, authenticate
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Sum  # 新增導入
from .models import CustomUser, ExamQuestion, ExamPaper, InteractionLog, StudentExamHistory, ExamAnswer, ExamRecord
from .forms import CustomLoginForm, CustomUserCreationForm, AvatarUpdateForm
import bleach
from django.utils.html import strip_tags
import re
import json

def home(request):
    return render(request, 'home.html')  # 首頁

def exam(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    
    current_time = timezone.now()
    
    if request.method == 'POST':
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
        
        elif 'paper_id' in request.POST:
            paper_id = request.POST.get('paper_id')
            if paper_id:
                try:
                    exam_paper = ExamPaper.objects.get(id=paper_id)
                    if current_time < exam_paper.start_time or current_time > exam_paper.end_time:
                        messages.error(request, "考試時間已過或尚未開始。")
                        return redirect('room:exam')

                    student = request.user
                    # 從 request.POST 獲取 answers 字段，假設前端傳送 JSON 字符串
                    answers_str = request.POST.get('answers', '{}')
                    print(f"Received answers string: {answers_str}")  # 調試：檢查傳入的 answers
                    try:
                        answers = json.loads(answers_str) if answers_str else {}
                        print(f"Parsed answers: {answers}")  # 調試：檢查解析後的 answers
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

                        # 處理 student_answer，允許空字符串但記錄
                        if student_answer is None or (isinstance(student_answer, list) and not any(student_answer)):
                            student_answer = None
                        elif isinstance(student_answer, str) and not student_answer.strip():
                            student_answer = ''  # 保留空字符串以區分未作答

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

                        # 確保保存 student_answer，即使為空
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

    # 獲取所有考卷並檢查完成狀態
    all_papers = ExamPaper.objects.all().prefetch_related('questions')
    exam_records = ExamRecord.objects.filter(student=request.user).values('exam_paper_id', 'is_completed')
    exam_records_dict = {record['exam_paper_id']: {'is_completed': record['is_completed']} for record in exam_records}

    # 過濾只顯示未結束且未完成的考試
    available_papers = [
        paper for paper in all_papers
        if paper.publish_time <= current_time and paper.end_time > current_time and
        not exam_records_dict.get(paper.id, {}).get('is_completed', False)
    ]
    for paper in available_papers:
        paper.ai_total_limit = sum(q.ai_limit for q in paper.questions.all())

    if not available_papers:
        messages.info(request, "目前沒有進行中的考試。請聯繫管理員或檢查時間設置。")

    return render(request, 'exam.html', {
        'exam_papers': available_papers,
        'exam_records': exam_records_dict,
        'user': request.user,
    })

def teacher_exam(request):
    """
    處理教師出題頁面，包括新增/編輯題目、題目庫管理及創建考試。
    僅限授權教師訪問。
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "您無權限訪問此頁面。")
        return render(request, 'teacher_exam.html')

    all_questions = ExamQuestion.objects.filter(created_by=request.user)
    question_types = {'sc': '單選題', 'mcq': '多選題', 'tf': '是非題', 'sa': '簡答題'}
    question_to_edit = None

    if request.method == 'POST':
        print("POST data:", dict(request.POST))
        print("FILES data:", dict(request.FILES))

        # 處理新增或編輯題目
        if 'question_text' in request.POST:
            question_id = request.POST.get('question_id')
            title = request.POST.get('title', '無題目標題').strip()
            ai_limit = request.POST.get('ai_limit', '1').strip()  # 預設為 1
            
            raw_content = request.POST.get('question_text', '').strip()
            print(f"Raw content: '{raw_content}'")
            
            # 檢查是否為 Quill 的空值
            if not raw_content or raw_content == '<p><br></p>' or raw_content == '':
                messages.error(request, "題目內容不能為空。")
                return render(request, 'teacher_exam.html', {
                    'all_questions': all_questions,
                    'question_to_edit': question_to_edit,
                    'question_types': question_types
                })

            content = bleach.clean(raw_content, tags=['p'], strip=True)
            if not content.startswith('<p>'):
                content = f'<p>{content}</p>'
            
            question_type = request.POST.get('question_type', 'sa')
            print(f"Question type: {question_type}")

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
                        'question_types': question_types
                    })

            is_correct = None
            correct_option_indices = None
            if question_type == 'sc':
                correct_option = request.POST.get('correct_option')
                print(f"SC correct option: {correct_option}")
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
                            'question_types': question_types
                        })
            
            elif question_type == 'mcq':
                correct_options = request.POST.getlist('correct_options')
                print(f"MCQ correct options: {correct_options}")
                if correct_options:
                    valid_options = [str(idx) for idx in map(int, correct_options) if 0 <= idx < len(options)]
                    if valid_options:
                        correct_option_indices = ','.join(sorted(valid_options))
            
            elif question_type == 'tf':
                tf_answer = request.POST.get('correct_answer', '').strip().lower()
                print(f"TF answer: '{tf_answer}'")
                if tf_answer in ['true', '1', 't', 'yes', 'y', '是', '對', '正確']:
                    is_correct = True
                elif tf_answer in ['false', '0', 'f', 'no', 'n', '否', '錯', '錯誤']:
                    is_correct = False
                else:
                    messages.error(request, "請選擇真或假作為正確答案。")
                    return render(request, 'teacher_exam.html', {
                        'all_questions': all_questions,
                        'question_to_edit': question_to_edit,
                        'question_types': question_types
                    })
            
            else:  # sa
                sa_answer = request.POST.get('correct_answer', '').strip()
                print(f"SA answer: '{sa_answer}'")
                correct_option_indices = sa_answer if sa_answer else None

            try:
                max_attempts = int(request.POST.get('max_attempts', 1))
                points = int(request.POST.get('points', 10))
                ai_limit = int(ai_limit)
                if max_attempts < 1 or points < 0 or points > 100 or ai_limit < 1:
                    raise ValueError("無效的嘗試次數、配分或 AI 問答次數限制")
            except (ValueError, TypeError) as e:
                messages.error(request, f"無效的嘗試次數、配分或 AI 問答次數限制：{str(e)}")
                return render(request, 'teacher_exam.html', {
                    'all_questions': all_questions,
                    'question_to_edit': question_to_edit,
                    'question_types': question_types
                })

            image = request.FILES.get('image') if 'image' in request.FILES else None

            print(f"Final data - Title: {title}, Content: {content}, Type: {question_type}, AI Limit: {ai_limit}")
            print(f"Options: {options}, is_correct: {is_correct}, correct_option_indices: {correct_option_indices}")

            try:
                if question_id:
                    exam_question = get_object_or_404(ExamQuestion, id=question_id, created_by=request.user)
                    exam_question.title = title
                    exam_question.content = content
                    exam_question.question_type = question_type
                    exam_question.options = options if options else None
                    exam_question.is_correct = is_correct
                    exam_question.correct_option_indices = correct_option_indices
                    exam_question.max_attempts = max_attempts
                    exam_question.points = points
                    exam_question.ai_limit = ai_limit
                    if image:
                        exam_question.image = image
                    exam_question.save()
                    messages.success(request, f"題目 '{title}' 已成功更新！")
                    print(f"Question updated: {exam_question.id}")
                else:
                    exam_question = ExamQuestion.objects.create(
                        title=title,
                        content=content,
                        question_type=question_type,
                        options=options if options else None,
                        is_correct=is_correct,
                        correct_option_indices=correct_option_indices,
                        max_attempts=max_attempts,
                        points=points,
                        ai_limit=ai_limit,
                        created_by=request.user,
                        image=image
                    )
                    print(f"Question created: {exam_question.id}")
                    InteractionLog.objects.create(
                        user=request.user,
                        question=f"題目: {content}, AI 次數限制: {ai_limit}",
                        response="題目已成功創建",
                        exam_question=exam_question,
                        exam_paper=None
                    )
                    messages.success(request, f"題目 '{title}' 已成功創建！")
            except IntegrityError as e:
                messages.error(request, "資料庫錯誤，請確保所有字段有效。")
                print(f"Database error: {str(e)}")
            except Exception as e:
                messages.error(request, f"創建/更新失敗：{str(e)}")
                print(f"Error creating/updating question: {str(e)}")

        # 處理創建考試
        elif 'action' in request.POST and request.POST['action'] == 'create_exam':
            exam_title = request.POST.get('exam_title').strip()
            selected_questions_str = request.POST.get('selected_questions', '').strip()

            if not selected_questions_str:
                messages.error(request, "請選擇至少一個題目。")
            else:
                try:
                    question_ids = [int(qid) for qid in selected_questions_str.split(',') if qid.strip()]
                    valid_questions = ExamQuestion.objects.filter(id__in=question_ids, created_by=request.user)
                    if not valid_questions.exists():
                        messages.error(request, f"所選題目無效或無權限。檢查 ID: {question_ids}")
                    else:
                        total_points = sum(q.points for q in valid_questions)
                        # 轉換為帶時區的 datetime
                        publish_time = timezone.datetime.strptime(request.POST.get('publish_time', timezone.now().strftime('%Y-%m-%dT%H:%M')), '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.get_current_timezone())
                        start_time = timezone.datetime.strptime(request.POST.get('start_time', timezone.now().strftime('%Y-%m-%dT%H:%M')), '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.get_current_timezone())
                        end_time = timezone.datetime.strptime(request.POST.get('end_time', (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')), '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.get_current_timezone())
                        duration_minutes = int(request.POST.get('duration_minutes', 60))

                        print(f"Processed times - publish: {publish_time}, start: {start_time}, end: {end_time}")

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
                            print(f"Exam paper created: {exam_paper.id}")
                except ValueError as e:
                    messages.error(request, f"時間或題目 ID 格式錯誤：{str(e)}")
                except Exception as e:
                    messages.error(request, f"創建考試失敗：{str(e)}")
                    print(f"Exception in exam creation: {e}")

        # 處理刪除題目
        elif 'delete_question' in request.POST:
            question_ids = request.POST.getlist('delete_questions')
            if question_ids:
                try:
                    question_ids = [int(qid) for qid in question_ids if qid.strip()]
                    deleted_count, _ = ExamQuestion.objects.filter(id__in=question_ids, created_by=request.user).delete()
                    if deleted_count > 0:
                        messages.success(request, f"成功刪除 {deleted_count} 個題目！")
                    else:
                        messages.warning(request, "未找到可刪除的題目或無權限。")
                except ValueError as e:
                    messages.error(request, f"題目 ID 格式錯誤：{str(e)}")
            else:
                messages.error(request, "請選擇至少一個題目進行刪除。")
        
        else:
            print("No matching POST condition found")
            print("Available POST keys:", list(request.POST.keys()))

    # 處理編輯題目
    edit_id = request.GET.get('edit')
    if edit_id:
        question_to_edit = get_object_or_404(ExamQuestion, id=edit_id, created_by=request.user)
        print(f"Editing question {edit_id}, is_correct: {question_to_edit.is_correct}, correct_option_indices: {question_to_edit.correct_option_indices}, type of is_correct: {type(question_to_edit.is_correct)}, type of correct_option_indices: {type(question_to_edit.correct_option_indices)}")
        if question_to_edit.options is None:
            question_to_edit.options = ['', '', '', '']
        while len(question_to_edit.options) < 4:
            question_to_edit.options.append('')
        if question_to_edit.content is None:
            question_to_edit.content = ''
        if question_to_edit.question_type == 'mcq' and question_to_edit.correct_option_indices:
            try:
                question_to_edit.correct_answer_list = question_to_edit.correct_option_indices.split(',')
            except:
                question_to_edit.correct_answer_list = []
        elif question_to_edit.question_type == 'sc' and question_to_edit.correct_option_indices:
            question_to_edit.correct_answer_list = [question_to_edit.correct_option_indices]
        else:
            question_to_edit.correct_answer_list = []

    return render(request, 'teacher_exam.html', {
        'all_questions': all_questions,
        'question_to_edit': question_to_edit,
        'question_types': question_types
    })

@login_required
def student_exam_history(request):
    """
    顯示每個學生的每個考試的每個題目答題紀錄。
    僅限已認證且具有管理權限的用戶訪問。
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "您無權限訪問此頁面。")
        return redirect('room:teacher_exam')

    # 獲取所有學生的考試歷史
    histories = StudentExamHistory.objects.all().order_by('-completed_at')
    detailed_records = []

    for history in histories:
        # 根據 student 和 exam_paper 查詢對應的 ExamRecord
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
                    'question_type': question.question_type,
                    'question_id': answer.exam_question.id,
                    'points': question.points,
                })
            detailed_records.append({
                'student_id': history.student.student_id,
                'exam_title': history.exam_paper.title,
                'total_score': history.total_score,
                'completed_at': history.completed_at,
                'answers': questions_with_answers,
            })

    if request.method == 'POST' and 'update_scores' in request.POST:
        student_exam_key = request.POST['update_scores'].split('_')
        student_id = student_exam_key[0]
        exam_title = '_'.join(student_exam_key[1:])
        history = StudentExamHistory.objects.filter(student__student_id=student_id, exam_paper__title=exam_title).first()

        if not history:
            messages.error(request, "找不到對應的考試歷史紀錄。")
            return render(request, 'student_exam_history.html', {'detailed_records': detailed_records})

        # 查詢對應的 ExamRecord
        exam_record = ExamRecord.objects.filter(
            student=history.student,
            exam_paper=history.exam_paper
        ).first()

        if not exam_record:
            messages.error(request, "找不到對應的考試紀錄。")
            return render(request, 'student_exam_history.html', {'detailed_records': detailed_records})

        total_score = 0
        for answer in exam_record.answer_details.all():
            question_title = answer.exam_question.title
            new_score = request.POST.get(f'score_{question_title}')
            if new_score is not None:
                try:
                    new_score = int(new_score)
                    max_score = answer.exam_question.points
                    if 0 <= new_score <= max_score:
                        answer.score = new_score
                        answer.is_correct = (new_score == max_score)
                        answer.save()
                        total_score += new_score
                    else:
                        messages.warning(request, f"題目 '{question_title}' 的調分 {new_score} 超出範圍 (0-{max_score})，未更新。")
                except ValueError:
                    messages.warning(request, f"題目 '{question_title}' 的調分無效，需為數字。")

        # 更新總分
        history.total_score = total_score
        history.save()
        exam_record.score = total_score
        exam_record.save()
        messages.success(request, f"已成功更新 {student_id} 的 '{exam_title}' 考試成績，總分為 {total_score}。")
        return redirect('room:student_exam_history')

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
            return redirect('home')
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
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def ask_ai(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt', '').strip()
        paper_id = request.POST.get('paper_id', '').strip()
        if not prompt or not paper_id:
            return JsonResponse({'response': '請提供問題和考卷 ID'}, status=400)

        try:
            paper = ExamPaper.objects.get(id=paper_id)
            used_count = InteractionLog.objects.filter(user=request.user, exam_paper=paper).count()
            if paper.ai_total_limit > 0 and used_count >= paper.ai_total_limit:
                return JsonResponse({'response': '已超過 AI 問答次數限制！'}, status=403)

            # 模擬 AI 回應（可替換為真實 API）
            response = f'這是對 "{prompt}" 的 AI 回覆（模擬）'
            InteractionLog.objects.create(
                user=request.user,
                question=prompt,
                response=response,
                exam_paper=paper
            )
            return JsonResponse({'response': response})
        except ExamPaper.DoesNotExist:
            return JsonResponse({'response': '考卷不存在'}, status=404)
    return JsonResponse({'response': '請使用 POST 方法提交提問'}, status=405)

def upload_question(request):
    if request.method == 'POST' and request.user.is_staff:
        title = request.POST.get('title', '無題目標題')
        content = request.POST.get('question', '')
        max_attempts = request.POST.get('max_attempts', 1)
        ai_limit = request.POST.get('ai_limit', 0)  # 新增：AI 問答次數限制
        image = request.FILES.get('image') if 'image' in request.FILES else None
        if content:
            exam_question = ExamQuestion.objects.create(
                title=title,
                content=content,
                max_attempts=max_attempts,
                ai_limit=ai_limit,  # 新增：儲存 ai_limit
                created_by=request.user,
                image=image
            )
            InteractionLog.objects.create(
                user=request.user,
                question=f"題目: {content}, 最大次數: {max_attempts}, AI 次數限制: {ai_limit}",
                response="題目已成功創建",
                exam_question=exam_question,
                exam_paper=None
            )
            return HttpResponse(f"題目 '{title}' 已上傳，最大提問次數: {max_attempts}，AI 問答次數限制: {ai_limit}")
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

            if not all([paper_id, question_id, answer is not None]):
                return JsonResponse({'status': 'error', 'message': '缺少必要參數'}, status=400)

            # 獲取相關物件
            exam_paper = get_object_or_404(ExamPaper, id=paper_id)
            exam_question = get_object_or_404(ExamQuestion, id=question_id)
            exam_record, created = ExamRecord.objects.get_or_create(
                student=request.user,
                exam_paper=exam_paper,
                defaults={'score': 0, 'is_completed': False}
            )

            # 檢查答題次數限制
            if exam_question.max_attempts > 0:
                answer_count = ExamAnswer.objects.filter(exam_record=exam_record, exam_question=exam_question).count()
                if answer_count >= exam_question.max_attempts:
                    return JsonResponse({'status': 'error', 'message': '已超過最大答題次數'}, status=403)

            # 判斷答案是否正確
            is_correct = False
            if exam_question.question_type == 'sc':
                try:
                    user_option = int(answer) if isinstance(answer, (int, str)) else None
                    correct_option = int(exam_question.correct_option_indices) if exam_question.correct_option_indices else None
                    is_correct = user_option == correct_option
                except (ValueError, TypeError):
                    is_correct = False
            elif exam_question.question_type == 'mcq':
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

            # 儲存答題紀錄
            exam_answer = ExamAnswer.objects.create(
                exam_record=exam_record,
                exam_question=exam_question,
                student_answer=str(answer) if answer else None,
                score=exam_question.points if is_correct else 0,
                is_correct=is_correct,
                answered_at=timezone.now()
            )

            # 更新總分
            total_score = ExamAnswer.objects.filter(exam_record=exam_record).aggregate(total=Sum('score'))['total'] or 0
            exam_record.score = total_score
            exam_record.save()

            # 記錄互動
            InteractionLog.objects.create(
                user=request.user,
                question=f"題目: {exam_question.title or exam_question.content[:50]}..., 回答: {answer or '未作答'}",
                response=f"回答 {'正確' if is_correct else '錯誤'}, 得分: {exam_answer.score}/{exam_question.points}",
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

logout = LogoutView.as_view(next_page='home')