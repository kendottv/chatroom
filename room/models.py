from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# 自訂用戶模型
class CustomUser(AbstractUser):
    student_id = models.CharField(max_length=8, unique=True, blank=True, null=True, verbose_name="學號")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="頭像")
    class_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="班級")  # 添加班級欄位

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "自訂使用者"
        verbose_name_plural = "自訂使用者"
# 考試題目模型，供老師上傳題目
class ExamQuestion(models.Model):
    title = models.CharField(max_length=200, verbose_name="題目標題")
    content = models.TextField(verbose_name="題目內容")
    image = models.ImageField(upload_to='exam_images/', blank=True, null=True, verbose_name="題目圖片")
    max_attempts = models.PositiveIntegerField(default=1, verbose_name="最大提問次數")
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="創建者")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "考試題目"
        verbose_name_plural = "考試題目"

# 提問與回答記錄模型，儲存使用者與 AI 的互動
class InteractionLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="使用者")
    question = models.TextField(verbose_name="提問內容")
    response = models.TextField(verbose_name="AI 回答")
    exam_question = models.ForeignKey(ExamQuestion, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="相關考試題目")
    attempt_count = models.PositiveIntegerField(default=1, verbose_name="提問次數")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="提問時間")

    def __str__(self):
        return f"{self.user.username} - {self.question[:50]}"

    class Meta:
        verbose_name = "互動記錄"
        verbose_name_plural = "互動記錄"