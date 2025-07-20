from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.core.files.storage import default_storage
from django.contrib.auth import login, authenticate
from django.utils import timezone
from .models import CustomUser, ExamQuestion, ExamPaper, InteractionLog
from .forms import CustomLoginForm, CustomUserCreationForm, AvatarUpdateForm

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
            if paper_id:
                try:
                    exam_paper = ExamPaper.objects.get(id=paper_id)
                    exam_paper.end_time = current_time
                    exam_paper.save()
                    messages.success(request, f"考卷 '{exam_paper.title}' 已結束！")
                except ExamPaper.DoesNotExist:
                    messages.error(request, "考卷不存在。")
        
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
                        # 正確的方式獲取每個問題的答案
                        answer_key = f'answers_{question.id}'
                        answer = request.POST.get(answer_key, '').strip()
                        
                        if answer:  # 只處理有答案的問題
                            answer_count += 1
                            is_correct = False
                            
                            # 根據題目類型判斷正確性
                            if hasattr(question, 'correct_answer') and question.correct_answer is not None:
                                if question.question_type == 'mcq':
                                    # 選擇題：比較選項索引
                                    is_correct = str(answer) == str(question.correct_answer)
                                elif question.question_type == 'tf':
                                    # 是非題：比較布林值
                                    is_correct = answer.lower() == question.correct_answer.lower()
                                elif question.question_type == 'sa' or question.question_type == 'essay':
                                    # 簡答題或問答題：比較答案（可以改進為更智能的比較）
                                    is_correct = answer.lower().strip() == question.correct_answer.lower().strip()
                            
                            # 計算得分
                            score = question.points if is_correct else 0
                            total_score += score
                            
                            # 記錄互動日誌
                            InteractionLog.objects.create(
                                user=request.user,
                                question=f"題目: {question.title or question.content[:50]}..., 回答: {answer}",
                                response=f"回答 {'正確' if is_correct else '錯誤' if hasattr(question, 'correct_answer') and question.correct_answer else '已記錄'}, 得分: {score}/{question.points}",
                                exam_question=question,
                                score=score
                            )
                    
                    # 檢查是否所有問題都已回答
                    if answer_count == questions.count():
                        messages.success(request, f"考卷提交成功！總得分: {total_score} / {exam_paper.total_points} 分")
                    elif answer_count > 0:
                        messages.warning(request, f"部分題目已提交。目前得分: {total_score} 分，請檢查是否有遺漏的題目。")
                    else:
                        messages.error(request, "請至少回答一個問題後再提交。")
                        
                except ExamPaper.DoesNotExist:
                    messages.error(request, "考卷不存在。")
                except Exception as e:
                    messages.error(request, f"提交過程中發生錯誤：{str(e)}")
        
        # 處理 AI 問答
        elif 'ai_question' in request.POST:
            ai_question = request.POST.get('ai_question', '').strip()
            if ai_question:
                # 這裡可以接入實際的 AI API，現在先用模擬回應
                ai_response = f"這是對 '{ai_question}' 的 AI 回覆（模擬）：請參考教材相關章節或與教師討論！"
                
                # 記錄 AI 互動
                InteractionLog.objects.create(
                    user=request.user,
                    question=ai_question,
                    response=ai_response
                )
                
                return JsonResponse({'response': ai_response})
            else:
                return JsonResponse({'response': '請輸入問題內容'})

    # 獲取可用的考試卷（GET 請求或處理完 POST 後）
    available_papers = ExamPaper.objects.filter(
        publish_time__lte=current_time,
        start_time__lte=current_time,
        end_time__gt=current_time
    ).prefetch_related('questions')  # 使用 prefetch_related 優化查詢效率
    
    # 添加調試信息（可以在開發時使用）
    if not available_papers.exists():
        messages.info(request, "目前沒有進行中的考試。請聯繫管理員或稍後再試。")
    
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
            content = request.POST.get('question_text', '')
            question_type = request.POST.get('question_type', 'sa')
            options = [request.POST.get(f'option_{i}') for i in range(1, 5) if request.POST.get(f'option_{i}') and request.POST.get(f'option_{i}').strip()]
            
            # 修改正確答案處理邏輯
            if question_type == 'mcq':
                # 多選題：獲取多個正確答案
                correct_options = request.POST.getlist('correct_options')
                correct_answer = ','.join(correct_options) if correct_options else ''
            elif question_type == 'sc':
                # 單選題：獲取單個正確答案
                correct_option = request.POST.get('correct_option')
                correct_answer = correct_option if correct_option and correct_option in [str(i) for i in range(1, len(options) + 1)] else ''
            elif question_type == 'tf':
                # 是非題
                correct_answer = request.POST.get('correct_answer', '')
            else:
                # 其他題型（如簡答題、申論題）
                correct_answer = request.POST.get('correct_answer', '')
            
            max_attempts = int(request.POST.get('max_attempts', 1))
            points = int(request.POST.get('points', 10))
            image = request.FILES.get('image') if 'image' in request.FILES else None

            if question_id:  # 編輯現有題目
                exam_question = get_object_or_404(ExamQuestion, id=question_id, created_by=request.user)
                exam_question.title = title
                exam_question.content = content
                exam_question.question_type = question_type
                exam_question.options = options if options else None
                exam_question.correct_answer = correct_answer if correct_answer else None
                exam_question.max_attempts = max_attempts
                exam_question.points = points
                if image:
                    exam_question.image = image
                exam_question.save()
                messages.success(request, f"題目 '{title}' 已成功更新！")
            else:  # 新增題目
                exam_question = ExamQuestion.objects.create(
                    title=title,
                    content=content,
                    question_type=question_type,
                    options=options if options else None,
                    correct_answer=correct_answer if correct_answer else None,
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
        elif 'exam_title' in request.POST:  # 創建考試
            exam_title = request.POST.get('exam_title')
            question_ids = request.POST.getlist('question_ids')
            total_points = sum(int(q.points) for q in ExamQuestion.objects.filter(id__in=question_ids))
            publish_time = timezone.datetime.strptime(request.POST.get('publish_time', timezone.now().strftime('%Y-%m-%dT%H:%M')), '%Y-%m-%dT%H:%M')
            start_time = timezone.datetime.strptime(request.POST.get('start_time', timezone.now().strftime('%Y-%m-%dT%H:%M')), '%Y-%m-%dT%H:%M')
            end_time = timezone.datetime.strptime(request.POST.get('end_time', (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')), '%Y-%m-%dT%H:%M')

            if start_time > end_time:
                messages.error(request, "開始時間不能晚於截止時間。")
            else:
                exam_paper = ExamPaper.objects.create(
                    title=exam_title,
                    total_points=total_points,
                    created_by=request.user,
                    publish_time=publish_time,
                    start_time=start_time,
                    end_time=end_time
                )
                exam_paper.questions.set(ExamQuestion.objects.filter(id__in=question_ids))
                messages.success(request, f"考卷 '{exam_title}' 已成功創建！")

    # 檢查編輯請求
    edit_id = request.GET.get('edit')
    if edit_id:
        question_to_edit = get_object_or_404(ExamQuestion, id=edit_id, created_by=request.user)
        # 確保 options 為列表，預設為空列表
        if question_to_edit.options is None:
            question_to_edit.options = ['', '', '', '']
        # 確保 content 為字符串
        if question_to_edit.content is None:
            question_to_edit.content = ''
        
        # 為編輯模式處理多選答案
        if question_to_edit.question_type == 'mcq' and question_to_edit.correct_answer:
            # 將多選答案分割成列表供模板使用
            question_to_edit.correct_answer_list = question_to_edit.correct_answer.split(',')
        else:
            question_to_edit.correct_answer_list = []
    else:
        question_to_edit = None

    # 傳遞 QUESTION_TYPES 給模板
    question_types = dict(ExamQuestion.QUESTION_TYPES)
    return render(request, 'teacher_exam.html', {'all_questions': all_questions, 'question_types': question_types, 'question_to_edit': question_to_edit})

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