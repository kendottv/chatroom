from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import authenticate
from .models import CustomUser

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