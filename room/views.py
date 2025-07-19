from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.core.files.storage import default_storage
from django.contrib.auth import login, authenticate
from .models import CustomUser, ExamQuestion, InteractionLog
from .forms import CustomLoginForm, CustomUserCreationForm

def home(request):
    return render(request, 'home.html')  # 首頁

def exam(request):
    return render(request, 'exam.html')  # 考試頁（做題）

def teacher_exam(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "您無權限訪問此頁面。")
        return render(request, 'teacher_exam.html')
    if request.method == 'POST':
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
            messages.success(request, f"題目 '{title}' 已成功上傳！")
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
    return render(request, 'profile.html', {'user': request.user})  # 個人資料頁

# 自訂登入視圖
def custom_login(request):
    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            student_id = form.cleaned_data['student_id']
            password = form.cleaned_data['password']
            user = authenticate(request, username=student_id, password=password)  # 使用 student_id 作為 username
            if user is not None:
                login(request, user)
                messages.success(request, f"歡迎，{user.username}！")
                return redirect('home')
            else:
                messages.error(request, "學號或密碼錯誤。")
    else:
        form = CustomLoginForm()
    return render(request, 'login.html', {'form': form})

# 註冊視圖
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # 註冊後自動登入
            messages.success(request, f"註冊成功，歡迎 {user.username}！")
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

# 臨時映射 view
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
        prompt = request.POST.get('prompt', '')
        response = f'對 "{prompt}" 的回饋（臨時）'
        InteractionLog.objects.create(
            user=request.user,
            question=prompt,
            response=response
        )
        return render(request, 'exam.html', {'exam_response': response})
    return HttpResponse("請使用 POST 方法提交回答。")

# 登出視圖
logout = LogoutView.as_view(next_page='home')