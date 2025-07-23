from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.contrib.auth import login, authenticate
from django.utils import timezone
from django.db import IntegrityError
from .models import CustomUser, ExamQuestion, ExamPaper, InteractionLog, StudentExamHistory, ExamAnswer, ExamRecord
from .forms import CustomLoginForm, CustomUserCreationForm, AvatarUpdateForm
import bleach
from django.utils.html import strip_tags
import re
def home(request):
    return render(request, 'home.html')  # 首頁

def exam(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    
    current_time = timezone.now()
    
    if request.method == 'POST':
        # 處理結束考試（管理員功能）
        if 'end_exam' in request.POST and request.user.is_staff:
            paper_id = request.POST.get('paper_id')
            print(f"Attempting to end exam with paper_id: {paper_id}")
            if paper_id:
                try:
                    exam_paper = ExamPaper.objects.get(id=paper_id)
                    exam_paper.end_time = current_time
                    exam_paper.save()
                    messages.success(request, f"考卷 '{exam_paper.title}' 已結束！")
                    return redirect('exam')
                except ExamPaper.DoesNotExist:
                    messages.error(request, "考卷不存在。")
            else:
                messages.error(request, "未提供考卷 ID。")
        
        # 處理考試答案提交
        elif 'paper_id' in request.POST:
            paper_id = request.POST.get('paper_id')
            if paper_id:
                try:
                    exam_paper = ExamPaper.objects.get(id=paper_id)
                    # 檢查考試是否在時間範圍內
                    if current_time < exam_paper.start_time or current_time > exam_paper.end_time:
                        messages.error(request, "考試時間已過或尚未開始。")
                        return redirect('exam')

                    student = request.user
                    answers = {}
                    # 收集所有答案
                    for key, value in request.POST.items():
                        if key.startswith('answers_'):
                            question_id = key.replace('answers_', '')
                            if value:
                                if request.POST.getlist(key):  # 處理多選題
                                    answers[question_id] = request.POST.getlist(key)
                                else:
                                    answers[question_id] = value

                    # 創建或更新 ExamRecord
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

                        # 處理空白答案
                        if not student_answer or student_answer == ['']:
                            student_answer = None

                        # 驗證答案
                        if student_answer is not None:
                            if question.question_type == 'sc':
                                try:
                                    user_option_index = int(student_answer[0]) if isinstance(student_answer, list) else int(student_answer)
                                    correct_option_index = int(question.correct_option_indices) if question.correct_option_indices else None
                                    is_correct = user_option_index == correct_option_index
                                except (ValueError, TypeError):
                                    is_correct = False
                            elif question.question_type == 'mcq':
                                try:
                                    user_options = sorted(student_answer) if isinstance(student_answer, list) else sorted(student_answer.split(',')) if student_answer else []
                                    correct_options = sorted(question.correct_option_indices.split(',')) if question.correct_option_indices else []
                                    is_correct = user_options == correct_options
                                except:
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

                        # 儲存到 ExamAnswer
                        ExamAnswer.objects.update_or_create(
                            exam_record=exam_record,
                            exam_question=question,
                            defaults={
                                'student_answer': str(student_answer) if student_answer else None,
                                'score': score,
                                'is_correct': is_correct
                            }
                        )

                        # 記錄到 InteractionLog
                        InteractionLog.objects.create(
                            user=student,
                            question=f"題目: {question.title or question.content[:50]}..., 回答: {student_answer or '未作答'}",
                            response=f"回答 {'正確' if is_correct else '錯誤' if question.correct_option_indices or question.is_correct else '已記錄'}, 得分: {score}/{question.points}",
                            exam_question=question,
                            score=score
                        )

                    # 更新考試歷史紀錄
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
                    return redirect('exam')

                except ExamPaper.DoesNotExist:
                    messages.error(request, "考卷不存在。")
                except Exception as e:
                    messages.error(request, f"提交過程中發生錯誤：{str(e)}")
                    print(f"Exception in exam submission: {e}")
        
        # 處理 AI 問答
        elif 'ai_question' in request.POST:
            ai_question = request.POST.get('ai_question', '').strip()
            if ai_question:
                ai_response = f"這是對 '{ai_question}' 的 AI 回覆（模擬）：請參考教材相關章節或與教師討論！"
                InteractionLog.objects.create(
                    user=request.user,
                    question=ai_question,
                    response=ai_response
                )
                return JsonResponse({'response': ai_response})
            else:
                return JsonResponse({'response': '請輸入問題內容'})

    # 獲取可用的考試卷，僅顯示未結束的考試
    available_papers = ExamPaper.objects.filter(
        publish_time__lte=current_time,
        end_time__gt=current_time
    ).prefetch_related('questions')
    
    # 除錯信息
    for paper in available_papers:
        print(f"ExamPaper {paper.id} - Title: {paper.title}, Questions: {paper.questions.count()}, Status: {'Active' if paper.end_time > current_time else 'Expired'}")
    if not available_papers.exists():
        messages.info(request, "目前沒有進行中的考試。請聯繫管理員或檢查時間設置。")
    
    return render(request, 'exam.html', {'exam_papers': available_papers})

def teacher_exam(request):
    """
    處理教師出題頁面，包括新增/編輯題目、題目庫管理及創建考試。
    僅限授權教師訪問。
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "您無權限訪問此頁面。")
        return render(request, 'teacher_exam.html')

    # 確保 all_questions 和 question_types 總是定義
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
            
            raw_content = request.POST.get('question_text', '').strip()
            print(f"Raw content: '{raw_content}'")
            
            if not raw_content:
                messages.error(request, "題目內容不能為空。")
            else:
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
                    if not options and question_type in ['sc', 'mcq']:
                        messages.error(request, "請至少填寫一個選項。")
                        return render(request, 'teacher_exam.html', {
                            'all_questions': all_questions,
                            'question_to_edit': question_to_edit,
                            'question_types': question_types
                        })

                is_correct = None
                correct_option_indices = None
                if question_type == 'mcq':
                    correct_options = request.POST.getlist('correct_options')
                    print(f"MCQ correct options: {correct_options}")
                    if correct_options:
                        valid_options = [str(idx) for idx in map(int, correct_options) if 0 <= idx < len(options)]
                        if valid_options:
                            correct_option_indices = ','.join(sorted(valid_options))
                
                elif question_type == 'sc':
                    correct_option = request.POST.get('correct_option')
                    print(f"SC correct option: {correct_option}")
                    if correct_option is not None:
                        try:
                            idx = int(correct_option)
                            if 0 <= idx < len(options):
                                correct_option_indices = str(idx)
                        except (ValueError, TypeError):
                            pass
                
                elif question_type == 'tf':
                    tf_answer = request.POST.get('correct_answer', '').strip().lower()
                    print(f"TF answer: '{tf_answer}'")
                    if tf_answer in ['true', '1', 't', 'yes', 'y', '是', '對', '正確']:
                        is_correct = True
                    elif tf_answer in ['false', '0', 'f', 'no', 'n', '否', '錯', '錯誤']:
                        is_correct = False
                    else:
                        is_correct = False
                
                else:  # sa
                    sa_answer = request.POST.get('correct_answer', '').strip()
                    print(f"SA answer: '{sa_answer}'")
                    correct_option_indices = sa_answer if sa_answer else None

                try:
                    max_attempts = int(request.POST.get('max_attempts', 1))
                    points = int(request.POST.get('points', 10))
                    if max_attempts < 1 or points < 0 or points > 100:
                        raise ValueError("無效的嘗試次數或配分")
                except (ValueError, TypeError) as e:
                    messages.error(request, f"無效的嘗試次數或配分：{str(e)}")
                    return render(request, 'teacher_exam.html', {
                        'all_questions': all_questions,
                        'question_to_edit': question_to_edit,
                        'question_types': question_types
                    })

                image = request.FILES.get('image') if 'image' in request.FILES else None

                print(f"Final data - Title: {title}, Content: {content}, Type: {question_type}")
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
                            created_by=request.user,
                            image=image
                        )
                        print(f"Question created: {exam_question.id}")
                        InteractionLog.objects.create(
                            user=request.user,
                            question=f"題目: {content}",
                            response="題目已成功創建",
                            exam_question=exam_question
                        )
                        messages.success(request, f"題目 '{title}' 已成功創建！")
                except IntegrityError as e:
                    messages.error(request, "資料庫錯誤，請確保所有字段有效。")
                    print(f"Database error: {str(e)}")
                except Exception as e:
                    messages.error(request, f"創建/更新失敗：{str(e)}")
                    print(f"Error creating/updating question: {str(e)}")

        # 處理創建考試
        elif 'exam_title' in request.POST:
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
                        publish_time = timezone.datetime.strptime(request.POST.get('publish_time', timezone.now().strftime('%Y-%m-%dT%H:%M')), '%Y-%m-%dT%H:%M')
                        start_time = timezone.datetime.strptime(request.POST.get('start_time', timezone.now().strftime('%Y-%m-%dT%H:%M')), '%Y-%m-%dT%H:%M')
                        end_time = timezone.datetime.strptime(request.POST.get('end_time', (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')), '%Y-%m-%dT%H:%M')
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

    return render(request, 'teacher_exam.html', {
        'all_questions': all_questions,
        'question_to_edit': question_to_edit,
        'question_types': question_types
    })

def student_exam_history(request):
    """
    顯示每個學生的每個考試的每個題目答題紀錄。
    僅限已認證且具有管理權限的用戶訪問。
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "您無權限訪問此頁面。")
        return redirect('teacher_exam')

    # 獲取所有學生的考試歷史
    histories = StudentExamHistory.objects.all().order_by('-completed_at')
    detailed_records = []

    for history in histories:
        exam_answers = ExamAnswer.objects.filter(exam_record__student=history.student, exam_record__exam_paper=history.exam_paper)
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
            })
        detailed_records.append({
            'student_id': history.student.student_id,
            'exam_title': history.exam_paper.title,
            'total_score': history.total_score,
            'completed_at': history.completed_at,
            'answers': questions_with_answers,
        })

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
    
    # 查詢學生所有的考試紀錄，包含考卷名稱和總分，按提交時間倒序排序
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
        prompt = request.POST.get('prompt', '')
        response = f'這是對 "{prompt}" 的 AI 回覆（模擬）'
        InteractionLog.objects.create(
            user=request.user,
            question=prompt,
            response=response
        )
        return render(request, 'exam.html', {'response': response})
    return HttpResponse("請使用 POST 方法提交提問。")

def upload_question(request):
    if request.method == 'POST' and request.user.is_staff:
        title = request.POST.get('title', '無題目標題')
        content = request.POST.get('question', '')
        max_attempts = request.POST.get('max_attempts', 1)
        image = request.FILES.get('image') if 'image' in request.FILES else None
        if content:
            exam_question = ExamQuestion.objects.create(
                title=title,
                content=content,
                max_attempts=max_attempts,
                created_by=request.user,
                image=image
            )
            InteractionLog.objects.create(
                user=request.user,
                question=f"題目: {content}, 最大次數: {max_attempts}",
                response="題目已成功創建",
                exam_question=exam_question
            )
            return HttpResponse(f"題目 '{title}' 已上傳，最大提問次數: {max_attempts}（臨時）")
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
                    is_correct = str(answer) in exam_question.correct_answer
                elif exam_question.question_type in ['sa', 'tf']:
                    is_correct = answer.lower() == exam_question.correct_answer.lower() if exam_question.correct_answer else False
                score = exam_question.points if is_correct else 0
                InteractionLog.objects.create(
                    user=request.user,
                    question=f"題目: {exam_question.title}, 回答: {answer}",
                    response=f"回答 {'正確' if is_correct else '錯誤'}, 得分: {score}",
                    exam_question=exam_question,
                    score=score
                )
                messages.success(request, f"回答提交成功！得分: {score} / {exam_question.points} 分")
            except ExamQuestion.DoesNotExist:
                messages.error(request, "題目不存在。")
        return redirect('exam')
    return HttpResponse("請使用 POST 方法提交回答。")

logout = LogoutView.as_view(next_page='home')