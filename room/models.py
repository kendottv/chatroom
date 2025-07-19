from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

# 自訂用戶模型
class CustomUser(AbstractUser):
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="學號")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="頭像")
    class_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="班級")

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "自訂使用者"
        verbose_name_plural = "自訂使用者"

# 考試題目模型
class ExamQuestion(models.Model):
    QUESTION_TYPES = (
        ('mcq', '選擇題'),
        ('essay', '問答題'),
        ('tf', '是非題'),
    )
    title = models.CharField(max_length=200, verbose_name="題目標題")
    content = models.TextField(verbose_name="題目內容")
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='essay', verbose_name="題型")  # 新增
    options = models.JSONField(default=list, blank=True, null=True, verbose_name="選項（選擇題專用）")  # 新增
    correct_answer = models.TextField(blank=True, null=True, verbose_name="正確答案")  # 改為 TextField 支援多行
    image = models.ImageField(upload_to='exam_images/', blank=True, null=True, verbose_name="題目圖片")
    max_attempts = models.PositiveIntegerField(default=1, verbose_name="最大提問次數")
    points = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="配分",
        help_text="每題配分 (0-100)"
    )
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="創建者")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    publish_time = models.DateTimeField(verbose_name="公佈時間", null=True, blank=True)
    start_time = models.DateTimeField(verbose_name="開始時間", null=True, blank=True)
    end_time = models.DateTimeField(verbose_name="截止時間", null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "考試題目"
        verbose_name_plural = "考試題目"

# 提問與回答記錄模型
class InteractionLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="使用者")
    question = models.TextField(verbose_name="提問內容")
    response = models.TextField(verbose_name="AI 回答")
    exam_question = models.ForeignKey(ExamQuestion, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="相關考試題目")
    attempt_count = models.PositiveIntegerField(default=1, verbose_name="提問次數")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="提問時間")
    score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="得分",
        help_text="題目得分 (0-100)"
    )

    def __str__(self):
        return f"{self.user.username} - {self.question[:50]}"

    class Meta:
        verbose_name = "互動記錄"
        verbose_name_plural = "互動記錄"