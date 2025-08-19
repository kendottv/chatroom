from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import authenticate
from .models import CustomUser, ExamQuestion, ExamPaper

# 登入表單
class CustomLoginForm(forms.Form):
    student_id = forms.CharField(max_length=20, label="學號", required=True)
    password = forms.CharField(widget=forms.PasswordInput(), label="密碼", required=True)

    def clean(self):
        cleaned_data = super().clean()
        student_id = cleaned_data.get("student_id")
        password = cleaned_data.get("password")

        if not student_id or not password:
            raise forms.ValidationError("請填寫學號和密碼。")

        # 根據學號找到對應的用戶
        try:
            user = CustomUser.objects.get(student_id=student_id)
        except CustomUser.DoesNotExist:
            raise forms.ValidationError("學號不存在。")

        # 使用 username 進行認證
        authenticated_user = authenticate(username=user.username, password=password)
        if authenticated_user is None:
            raise forms.ValidationError("密碼錯誤。")

        if not authenticated_user.is_active:
            raise forms.ValidationError("該帳戶已被停用。")

        cleaned_data['user'] = authenticated_user
        return cleaned_data

# 註冊表單
class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, label="姓名", required=True)
    class_name = forms.CharField(max_length=50, label="班級", required=True)
    student_id = forms.CharField(max_length=20, label="學號", required=True)

    class Meta:
        model = CustomUser
        fields = ('first_name', 'student_id', 'class_name', 'password1', 'password2')

    def clean_student_id(self):
        student_id = self.cleaned_data['student_id']
        if CustomUser.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("此學號已被註冊。")
        return student_id

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.student_id = self.cleaned_data['student_id']
        user.class_name = self.cleaned_data['class_name']
        user.username = self.cleaned_data['student_id']  # 使用學號作為用戶名
        if commit:
            user.save()
        return user

# 更改頭像表單
class AvatarUpdateForm(forms.ModelForm):
    avatar = forms.ImageField(label="上傳新頭像", required=False)

    class Meta:
        model = CustomUser
        fields = ('avatar',)

# 題目表單
class QuestionForm(forms.ModelForm):
    """
    表單用於新增或編輯考試題目，支援題目標題、題型、內容、選項、正確答案、嘗試次數、配分、圖片和 AI 問答次數限制。
    """
    class Meta:
        model = ExamQuestion
        fields = ['title', 'question_type', 'content', 'options', 'correct_option_indices', 'is_correct', 'max_attempts', 'points', 'image', 'ai_limit']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '輸入題目標題'}),
            'content': forms.Textarea(attrs={'rows': 5, 'placeholder': '輸入題目內容'}),
            'options': forms.Textarea(attrs={'rows': 4, 'placeholder': '輸入選項，每行一個（僅限單選/多選題）'}),
            'correct_option_indices': forms.TextInput(attrs={'placeholder': '輸入正確選項索引（例如：0 或 0,1）'}),
            'max_attempts': forms.NumberInput(attrs={'min': 1, 'value': 1}),
            'points': forms.NumberInput(attrs={'min': 0, 'max': 100, 'value': 10}),
            'ai_limit': forms.NumberInput(attrs={'min': 0, 'value': 0, 'placeholder': '0 表示無限制'}),
            'image': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def clean(self):
        """
        自訂驗證，確保題型相關欄位有效，並檢查 AI 問答次數限制。
        """
        cleaned_data = super().clean()
        question_type = cleaned_data.get('question_type')
        options = cleaned_data.get('options')
        correct_option_indices = cleaned_data.get('correct_option_indices')
        is_correct = cleaned_data.get('is_correct')
        ai_limit = cleaned_data.get('ai_limit')

        # 驗證單選/多選題
        if question_type in ['sc', 'mcq']:
            if not options:
                raise forms.ValidationError("單選或多選題必須提供選項。")
            if not correct_option_indices:
                raise forms.ValidationError("請指定正確選項索引。")
            try:
                option_list = [opt.strip() for opt in options.split('\n') if opt.strip()]
                indices = [int(idx) for idx in correct_option_indices.split(',') if idx.strip()]
                for idx in indices:
                    if idx < 0 or idx >= len(option_list):
                        raise forms.ValidationError("正確選項索引超出範圍。")
            except (ValueError, TypeError):
                raise forms.ValidationError("正確選項索引格式錯誤。")
        # 驗證是非題
        elif question_type == 'tf':
            if is_correct is None:
                raise forms.ValidationError("是非題必須指定正確答案。")
        # 驗證 AI 問答次數限制
        if ai_limit is not None and ai_limit < 0:
            raise forms.ValidationError("AI 問答次數限制不能為負數。")

        return cleaned_data

# 考試表單
class ExamPaperForm(forms.ModelForm):
    """
    表單用於創建考試，包含考試名稱、說明、時間設置和題目選擇。
    selected_questions 用於接收題目 ID 列表。
    """
    selected_questions = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = ExamPaper
        fields = ['title', 'description', 'publish_time', 'start_time', 'end_time', 'duration_minutes']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '輸入考試名稱'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': '輸入考試說明（選填）'}),
            'publish_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'duration_minutes': forms.NumberInput(attrs={'min': 5, 'max': 300, 'value': 60}),
        }

    def clean(self):
        """
        驗證考試時間設置和選中題目。
        """
        cleaned_data = super().clean()
        publish_time = cleaned_data.get('publish_time')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        duration_minutes = cleaned_data.get('duration_minutes')
        selected_questions = cleaned_data.get('selected_questions')

        # 驗證時間順序
        if publish_time and start_time and publish_time > start_time:
            raise forms.ValidationError("發佈時間不能晚於開始時間。")
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError("開始時間必須早於截止時間。")
        if duration_minutes and (duration_minutes < 5 or duration_minutes > 300):
            raise forms.ValidationError("考試時長必須在 5 到 300 分鐘之間。")
        
        # 驗證選中題目
        if not selected_questions:
            raise forms.ValidationError("請至少選擇一題。")
        try:
            question_ids = [int(qid) for qid in selected_questions.split(',') if qid]
            if not question_ids:
                raise forms.ValidationError("請選擇有效題目。")
        except ValueError:
            raise forms.ValidationError("選中題目格式錯誤。")

        return cleaned_data