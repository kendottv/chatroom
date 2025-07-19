from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import CustomUser

# 登入表單
class CustomLoginForm(AuthenticationForm):
    student_id = forms.CharField(max_length=20, label="學號", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = forms.HiddenInput()
        self.fields['password'].label = "密碼"
        self.order_fields(['student_id', 'password']) 

    def clean(self):
        cleaned_data = super().clean()
        student_id = cleaned_data.get("student_id")
        password = cleaned_data.get("password")

        if not student_id or not password:
            raise forms.ValidationError("請填寫學號和密碼。")

        user = CustomUser.objects.filter(student_id=student_id).first()
        if not user:
            raise forms.ValidationError("學號不存在。")

        cleaned_data['username'] = user.username
        return cleaned_data


# 註冊表單
class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, label="姓名", required=True)
    class_name = forms.CharField(max_length=50, label="班級", required=True)
    student_id = forms.CharField(max_length=20, label="學號", required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'student_id', 'class_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 隱藏 username 欄位，並讓它不再是 required
        self.fields['username'].widget = forms.HiddenInput()
        self.fields['username'].required = False  

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.student_id = self.cleaned_data['student_id']
        user.class_name = self.cleaned_data['class_name']
        user.username = self.cleaned_data['student_id']  # 將 username 設為學號
        if commit:
            user.save()
        return user
