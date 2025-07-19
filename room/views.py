from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.core.files.storage import default_storage
from django.contrib.auth import login, authenticate
from django.utils import timezone
from .models import CustomUser, ExamQuestion, InteractionLog
from .forms import CustomLoginForm, CustomUserCreationForm, AvatarUpdateForm

def home(request):
    return render(request, 'home.html')  # 首頁

def exam(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    
    current_time = timezone.now()
    if request.method == 'POST':
        if request.user.is_staff and 'end_exam' in request.POST:
            question_id = request.POST.get('question_id')
            if question_id:
                try:
                    exam_question = ExamQuestion.objects.get(id=question_id)
                    exam_question.end_time = current_time  # 將結束時間設為當前時間
                    exam_question.save()
                    messages.success(request, f"題目 '{exam_question.title}' 已結束！")
                except ExamQuestion.DoesNotExist:
                    messages.error(request, "題目不存在。")
        else:
            question_id = request.POST.get('question_id')
            answer = request.POST.get('answer', '').strip()
            if question_id:
                try:
                    exam_question = ExamQuestion.objects.get(id=question_id)
                    is_correct = False
                    if exam_question.question_type == 'mcq':
                        is_correct = answer in exam_question.correct_answer
                    elif exam_question.question_type in ['essay', 'tf']:
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
    
    # 過濾可用題目，end_time 大於當前時間
    available_questions = ExamQuestion.objects.filter(
        publish_time__lte=current_time,
        start_time__lte=current_time,
        end_time__gt=current_time
    )
    print(f"當前時間: {current_time}, 可用題目數: {available_questions.count()}")
    for q in available_questions:
        print(f"題目: {q.title}, 公佈時間: {q.publish_time}, 開始時間: {q.start_time}, 截止時間: {q.end_time}")

    return render(request, 'exam.html', {'exam_questions': available_questions})

def teacher_exam(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "您無權限訪問此頁面。")
        return render(request, 'teacher_exam.html')
    
    if request.method == 'POST':
        title = request.POST.get('title', '無題目標題')
        content = request.POST.get('question', '')
        question_type = request.POST.get('question_type', 'essay')
        options = request.POST.getlist('options') if request.POST.getlist('options') else []
        correct_answer = request.POST.get('correct_answer', '')
        max_attempts = request.POST.get('max_attempts', 1)
        points = request.POST.get('points', 10)
        publish_time = request.POST.get('publish_time')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        image = request.FILES.get('image') if 'image' in request.FILES else None
        
        if content:
            try:
                points = int(points)
                if not 0 <= points <= 100:
                    raise ValueError("配分必須在 0-100 之間。")
                
                publish_time = timezone.datetime.strptime(publish_time, '%Y-%m-%d %H:%M') if publish_time else timezone.now()
                start_time = timezone.datetime.strptime(start_time, '%Y-%m-%d %H:%M') if start_time else timezone.now()
                end_time = timezone.datetime.strptime(end_time, '%Y-%m-%d %H:%M') if end_time else timezone.now() + timezone.timedelta(hours=1)
                
                if start_time > end_time:
                    raise ValueError("開始時間不能晚於截止時間。")
                
                if question_type == 'mcq' and options:
                    options = [opt for opt in options if opt]
                    if not options:
                        raise ValueError("選擇題必須提供至少一個選項。")
                    if correct_answer not in options:
                        raise ValueError("正確答案必須在選項中。")
                elif question_type == 'tf':
                    if correct_answer not in ['true', 'false', 'True', 'False']:
                        raise ValueError("是非題正確答案必須為 true 或 false。")
                
                exam_question = ExamQuestion.objects.create(
                    title=title,
                    content=content,
                    question_type=question_type,
                    options=options if question_type == 'mcq' else None,
                    correct_answer=correct_answer,
                    max_attempts=max_attempts,
                    points=points,
                    created_by=request.user,
                    image=image,
                    publish_time=publish_time,
                    start_time=start_time,
                    end_time=end_time
                )
                InteractionLog.objects.create(
                    user=request.user,
                    question=f"題目: {content}, 最大次數: {max_attempts}, 配分: {points}",
                    response="題目已成功創建",
                    exam_question=exam_question
                )
                messages.success(request, f"題目 '{title}' 已成功上傳！配分: {points} 分")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"錯誤: {str(e)}")
    
    return render(request, 'teacher_exam.html')

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
        print("收到 POST 請求，開始處理登入")
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            print("表單驗證成功")
            user = form.cleaned_data['user']
            print(f"登入用戶: {user.username}")
            login(request, user)
            print("登入成功")
            messages.success(request, f"歡迎，{user.username}！")
            return redirect('home')
        else:
            print("表單驗證失敗")
            for error in form.errors.values():
                print(error)
    else:
        print("收到 GET 請求，顯示登入表單")
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
        response = f'這是對 "{prompt}" 的 AI 回覆（臨時）'
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
                    is_correct = answer in exam_question.correct_answer
                elif exam_question.question_type in ['essay', 'tf']:
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