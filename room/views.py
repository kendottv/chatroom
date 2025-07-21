from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.core.files.storage import default_storage
from django.contrib.auth import login, authenticate
from django.utils import timezone
from .models import CustomUser, ExamQuestion, ExamPaper, InteractionLog
from .forms import CustomLoginForm, CustomUserCreationForm, AvatarUpdateForm
import bleach
from django.utils.html import strip_tags
import re

def home(request):
    return render(request, 'home.html')  # 首頁

# 修復 exam 函數中的答案驗證邏輯
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
                    questions = exam_paper.questions.all()
                    total_score = 0
                    answer_count = 0
                    
                    for question in questions:
                        answer_key = f'answers_{question.id}'
                        answer = request.POST.get(answer_key, '').strip()
                        
                        if answer:
                            answer_count += 1
                            is_correct = False
                            
                            # 修復答案驗證邏輯
                            if hasattr(question, 'correct_answer') and question.correct_answer is not None:
                                print(f"Question {question.id}: type={question.question_type}, user_answer='{answer}', correct_answer='{question.correct_answer}'")
                                
                                if question.question_type == 'sc':
                                    # 單選題：比較選項索引
                                    try:
                                        user_option_index = int(answer)
                                        correct_option_index = int(question.correct_answer)
                                        is_correct = user_option_index == correct_option_index
                                        print(f"SC: user={user_option_index}, correct={correct_option_index}, is_correct={is_correct}")
                                    except (ValueError, TypeError):
                                        is_correct = False
                                        
                                elif question.question_type == 'mcq':
                                    # 多選題：比較選項索引組合
                                    try:
                                        user_options = set(answer.split(',')) if ',' in answer else {answer}
                                        correct_options = set(question.correct_answer.split(','))
                                        is_correct = user_options == correct_options
                                        print(f"MCQ: user={user_options}, correct={correct_options}, is_correct={is_correct}")
                                    except:
                                        is_correct = False
                                        
                                elif question.question_type == 'tf':
                                    # 是非題：直接比較字符串
                                    is_correct = answer.lower() == question.correct_answer.lower()
                                    print(f"TF: user='{answer.lower()}', correct='{question.correct_answer.lower()}', is_correct={is_correct}")
                                    
                                elif question.question_type in ['sa', 'essay']:
                                    # 簡答題和論述題：字符串比較（去除空格和大小寫）
                                    is_correct = answer.lower().strip() == question.correct_answer.lower().strip()
                                    print(f"SA/Essay: user='{answer.lower().strip()}', correct='{question.correct_answer.lower().strip()}', is_correct={is_correct}")
                            
                            score = question.points if is_correct else 0
                            total_score += score
                            
                            InteractionLog.objects.create(
                                user=request.user,
                                question=f"題目: {question.title or question.content[:50]}..., 回答: {answer}",
                                response=f"回答 {'正確' if is_correct else '錯誤' if hasattr(question, 'correct_answer') and question.correct_answer else '已記錄'}, 得分: {score}/{question.points}",
                                exam_question=question,
                                score=score
                            )
                    
                    if answer_count == questions.count():
                        messages.success(request, f"考卷提交成功！總得分: {total_score} / {exam_paper.total_points} 分")
                        exam_paper.end_time = current_time
                        exam_paper.save()
                        return redirect('exam')
                    elif answer_count > 0:
                        messages.warning(request, f"部分題目已提交。目前得分: {total_score} 分，請檢查是否有遺漏的題目。")
                    else:
                        messages.error(request, "請至少回答一個問題後再提交。")
                        
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
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "您無權限訪問此頁面。")
        return render(request, 'teacher_exam.html')
    
    all_questions = ExamQuestion.objects.filter(created_by=request.user)
    question_to_edit = None

    if request.method == 'POST':
        if 'question_text' in request.POST:  # 新增或編輯題目
            question_id = request.POST.get('question_id')
            title = request.POST.get('title', '無題目標題')
            # 清理 HTML 標籤，僅允許 <p> 標籤並移除空 <p>
            content = bleach.clean(request.POST.get('question_text', ''), tags=['p'], strip=True)
            content = re.sub(r'<p>\s*</p>', '', content)  # 移除空 <p> 標籤
            content = strip_tags(content).strip() or '<p>' + strip_tags(content).strip() + '</p>'  # 確保至少有一個有效段落
            question_type = request.POST.get('question_type', 'sa')
            
            # 修復選項處理邏輯
            options = []
            for i in range(1, 5):  # 選項1到選項4
                option_value = request.POST.get(f'option_{i}', '').strip()
                if option_value:
                    options.append(option_value)
            
            # 如果是選擇題但沒有選項，添加預設選項
            if question_type in ['sc', 'mcq'] and not options:
                options = ['選項1', '選項2', '選項3', '選項4']
            
            # 修復正確答案處理邏輯
            correct_answer = None
            if question_type == 'mcq':
                # 多選題：獲取所有選中的選項索引
                correct_options = request.POST.getlist('correct_options')
                print(f"MCQ correct_options received: {correct_options}")
                
                # 驗證選項索引有效性
                valid_options = []
                for opt_idx in correct_options:
                    try:
                        idx = int(opt_idx)
                        if 0 <= idx < len(options):
                            valid_options.append(str(idx))
                    except (ValueError, TypeError):
                        continue
                
                if valid_options:
                    correct_answer = ','.join(sorted(valid_options))
                    print(f"MCQ correct_answer saved: {correct_answer}")
                
            elif question_type == 'sc':
                # 單選題：獲取選中的選項索引
                correct_option = request.POST.get('correct_option')
                print(f"SC correct_option received: {correct_option}")
                
                if correct_option is not None:
                    try:
                        idx = int(correct_option)
                        if 0 <= idx < len(options):
                            correct_answer = str(idx)
                            print(f"SC correct_answer saved: {correct_answer}")
                    except (ValueError, TypeError):
                        pass
                        
            elif question_type == 'tf':
                # 是非題
                tf_answer = request.POST.get('correct_answer', '').lower()
                correct_answer = 'true' if tf_answer in ['true', '1', 't'] else 'false'
                print(f"TF correct_answer saved: {correct_answer}")
                
            else:  # sa, essay
                # 簡答題或論述題
                correct_answer = request.POST.get('correct_answer', '').strip() or None
            
            max_attempts = int(request.POST.get('max_attempts', 1))
            points = int(request.POST.get('points', 10))
            image = request.FILES.get('image') if 'image' in request.FILES else None

            print(f"Final data - Options: {options}, Correct Answer: {correct_answer}")

            if question_id:  # 編輯現有題目
                exam_question = get_object_or_404(ExamQuestion, id=question_id, created_by=request.user)
                exam_question.title = title
                exam_question.content = content
                exam_question.question_type = question_type
                exam_question.options = options if options else None
                exam_question.correct_answer = correct_answer
                exam_question.max_attempts = max_attempts
                exam_question.points = points
                if image:
                    exam_question.image = image
                exam_question.save()
                messages.success(request, f"題目 '{title}' 已成功更新！")
                print(f"Updated question {question_id}: options={exam_question.options}, correct_answer={exam_question.correct_answer}")
                
            else:  # 新增題目
                exam_question = ExamQuestion.objects.create(
                    title=title,
                    content=content,
                    question_type=question_type,
                    options=options if options else None,
                    correct_answer=correct_answer,
                    max_attempts=max_attempts,
                    points=points,
                    created_by=request.user,
                    image=image
                )
                InteractionLog.objects.create(
                    user=request.user,
                    question=f"題目: {content}",
                    response="題目已成功創建",
                    exam_question=exam_question
                )
                messages.success(request, f"題目 '{title}' 已成功創建！")
                print(f"Created question {exam_question.id}: options={exam_question.options}, correct_answer={exam_question.correct_answer}")
                
        elif 'exam_title' in request.POST:  # 創建考試
            exam_title = request.POST.get('exam_title')
            selected_questions_str = request.POST.get('selected_questions', '').strip()
            print(f"Received selected_questions string: {selected_questions_str}")
    
            if not selected_questions_str:
                messages.error(request, "請選擇至少一個題目。")
            else:
                try:
                    # 分割並轉換為整數列表
                    question_ids = [int(qid) for qid in selected_questions_str.split(',') if qid.strip()]
                    print(f"Converted question_ids: {question_ids}")
                    valid_questions = ExamQuestion.objects.filter(id__in=question_ids, created_by=request.user)
                    print(f"Valid questions count: {valid_questions.count()}, IDs: {[q.id for q in valid_questions]}")
                    if not valid_questions.exists():
                        messages.error(request, f"所選題目無效或無權限。檢查 ID: {question_ids}")
                    else:
                        total_points = sum(int(q.points) for q in valid_questions)
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
                                description=request.POST.get('exam_description', '')
                            )
                            exam_paper.questions.set(valid_questions)
                            print(f"Set questions for paper {exam_paper.id}: {exam_paper.questions.count()}")
                            messages.success(request, f"考卷 '{exam_title}' 已成功創建！")
                except ValueError as e:
                    messages.error(request, f"時間或題目 ID 格式錯誤：{str(e)}")
                    print(f"ValueError details: {e}, input was: {selected_questions_str}")
        elif 'delete_question' in request.POST:  # 刪除題目
            question_ids = request.POST.getlist('delete_questions')
            print(f"Received delete question_ids: {question_ids}")
            if question_ids:
                try:
                    question_ids = [int(qid) for qid in question_ids if qid.strip()]
                    deleted_count = ExamQuestion.objects.filter(id__in=question_ids, created_by=request.user).delete()[0]
                    if deleted_count > 0:
                        messages.success(request, f"成功刪除 {deleted_count} 個題目！")
                    else:
                        messages.warning(request, "未找到可刪除的題目或無權限。")
                except ValueError as e:
                    messages.error(request, f"題目 ID 格式錯誤：{str(e)}")
            else:
                messages.error(request, "請選擇至少一個題目進行刪除。")

    # 處理編輯題目的邏輯
    edit_id = request.GET.get('edit')
    if edit_id:
        question_to_edit = get_object_or_404(ExamQuestion, id=edit_id, created_by=request.user)
        
        # 確保選項數據完整性
        if question_to_edit.options is None:
            question_to_edit.options = ['', '', '', '']
        else:
            # 確保有4個選項位置供編輯
            while len(question_to_edit.options) < 4:
                question_to_edit.options.append('')
        
        # 處理內容為空的情況
        if question_to_edit.content is None:
            question_to_edit.content = ''
        
        # 處理多選題的正確答案列表
        if question_to_edit.question_type == 'mcq' and question_to_edit.correct_answer:
            try:
                question_to_edit.correct_answer_list = question_to_edit.correct_answer.split(',')
            except:
                question_to_edit.correct_answer_list = []
        else:
            question_to_edit.correct_answer_list = []
            
        print(f"Editing question {edit_id}: options={question_to_edit.options}, correct_answer={question_to_edit.correct_answer}, type={question_to_edit.question_type}")

    question_types = dict(ExamQuestion.QUESTION_TYPES)
    return render(request, 'teacher_exam.html', {
        'all_questions': all_questions, 
        'question_types': question_types, 
        'question_to_edit': question_to_edit
    })

def readme(request):
    return render(request, 'readme.html')  # ReadMe 頁

def history(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    history_records = InteractionLog.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'history.html', {'history_records': history_records})  # 歷史頁

def profile(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    
    exam_scores = InteractionLog.objects.filter(user=request.user, exam_question__isnull=False).values(
        'exam_question__title', 'score', 'exam_question__points'
    )
    
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
        'exam_scores': exam_scores,
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