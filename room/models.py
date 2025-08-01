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
        ('sc', 'Single Choice'),
        ('mcq', 'Multiple Choice'),
        ('tf', 'True/False'),
        ('sa', 'Short Answer'),
    )
    title = models.CharField(max_length=200, verbose_name="題目標題")
    content = models.TextField(verbose_name="題目內容")
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='sa', verbose_name="題型")
    options = models.JSONField(null=True, blank=True, verbose_name="選項列表")  # 例如 ["a", "b", "c"] 或 [1, 2, 3]
    is_correct = models.BooleanField(default=False, verbose_name="是否正確", null=True, blank=True)  # 專用於 tf 題型
    correct_option_indices = models.TextField(null=True, blank=True, verbose_name="正確選項索引")  # 專用於 sc 和 mcq
    max_attempts = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="最大嘗試次數")
    points = models.IntegerField(default=10, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="配分")
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="創建者")
    image = models.ImageField(upload_to='questions/', null=True, blank=True, verbose_name="題目圖片")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "考試題目"
        verbose_name_plural = "考試題目"

# 考卷模型
class ExamPaper(models.Model):
    title = models.CharField(max_length=200, verbose_name="考卷名稱")
    questions = models.ManyToManyField(ExamQuestion, verbose_name="包含題目")
    total_points = models.IntegerField(default=0, verbose_name="總分")
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="創建者")
    publish_time = models.DateTimeField(default=timezone.now, verbose_name="發佈時間")
    start_time = models.DateTimeField(default=timezone.now, verbose_name="開始時間")
    end_time = models.DateTimeField(default=timezone.now, verbose_name="截止時間")
    pdf_file = models.FileField(upload_to='exam_papers/', null=True, blank=True, verbose_name="考卷 PDF")
    duration_minutes = models.IntegerField(default=60, validators=[MinValueValidator(1)], verbose_name="考試持續時間（分鐘）")
    description = models.TextField(blank=True, default='', verbose_name="考試描述")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "考卷"
        verbose_name_plural = "考卷"

class InteractionLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="使用者")
    question = models.TextField(verbose_name="問題")
    response = models.TextField(verbose_name="回覆")
    exam_question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE, null=True, blank=True, verbose_name="相關題目")
    score = models.IntegerField(default=0, verbose_name="得分")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="創建時間")

    def __str__(self):
        return f"{self.user.username} - {self.question[:50]}"

    class Meta:
        verbose_name = "互動記錄"
        verbose_name_plural = "互動記錄"

# 學生考試紀錄模型
class ExamRecord(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, to_field='student_id', related_name='exam_records', verbose_name="學生")
    exam_paper = models.ForeignKey(ExamPaper, on_delete=models.CASCADE, verbose_name="考卷")
    score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="總分")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="提交時間")
    is_completed = models.BooleanField(default=False, verbose_name="是否完成")

    def __str__(self):
        return f"{self.student.student_id} - {self.exam_paper.title}"

    class Meta:
        verbose_name = "考試紀錄"
        verbose_name_plural = "考試紀錄"
        unique_together = ('student', 'exam_paper')  # 確保一個學生對同一考卷只有一筆紀錄

# 學生對每個題目的答題紀錄
class ExamAnswer(models.Model):
    exam_record = models.ForeignKey(ExamRecord, on_delete=models.CASCADE, related_name='answer_details', verbose_name="考試紀錄")
    exam_question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE, verbose_name="題目")
    student_answer = models.TextField(null=True, blank=True, verbose_name="學生答案")  # 儲存單一題的答案
    score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="得分")
    is_correct = models.BooleanField(default=False, verbose_name="是否正確")
    answered_at = models.DateTimeField(auto_now_add=True, verbose_name="回答時間")

    def __str__(self):
        return f"{self.exam_record.student.student_id} - Q{self.exam_question.id}: {self.student_answer}"

    class Meta:
        verbose_name = "答題紀錄"
        verbose_name_plural = "答題紀錄"
        unique_together = ('exam_record', 'exam_question')  # 確保一個紀錄中不重複記錄同一題

# 學生考試歷史紀錄（分開用於查看）
class StudentExamHistory(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, to_field='student_id', related_name='exam_history', verbose_name="學生")
    exam_paper = models.ForeignKey(ExamPaper, on_delete=models.CASCADE, verbose_name="考卷")
    total_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="總分")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成時間")
    grade = models.CharField(max_length=10, blank=True, null=True, verbose_name="等級")  # 例如 A, B, C

    def __str__(self):
        return f"{self.student.student_id} - {self.exam_paper.title} (得分: {self.total_score})"

    class Meta:
        verbose_name = "考試歷史紀錄"
        verbose_name_plural = "考試歷史紀錄"
        unique_together = ('student', 'exam_paper')  # 確保一個學生對同一考卷只有一筆歷史紀錄