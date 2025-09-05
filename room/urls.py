from django.urls import path
from . import views

app_name = 'room'  # 定義命名空間

urlpatterns = [
    path('', views.home, name='home'),  # 首頁
    path('exam/', views.exam, name='exam'),  # 考試頁（做題）
    path('exam/select/', views.select_exam, name='select_exam'),  # 選擇考卷頁面
    path('teacher_exam/', views.teacher_exam, name='teacher_exam'),  # 出題頁
    path('readme/', views.readme, name='readme'),  # ReadMe 頁
    path('history/', views.history, name='history'),  # 歷史頁
    path('login/', views.custom_login, name='login'),  # 自訂登入頁
    path('register/', views.register, name='register'),  # 註冊頁
    path('logout/', views.logout, name='logout'),  # 登出
    path('profile/', views.profile, name='profile'),  # 個人資料頁
    path('ask_ai/', views.ask_ai, name='ask_ai'),  # AI 提問
    path('upload_question/', views.upload_question, name='upload_question'),  # 出題提交
    path('ask_exam_question/', views.ask_exam_question, name='ask_exam_question'),  # 回答問題
    path('student_exam_history/', views.student_exam_history, name='student_exam_history'),
    path('submit_single_answer/', views.submit_single_answer, name='submit_single_answer'),
    path("webhooks/ai/", views.ai_webhook, name="ai_webhook"),  # 新增路由
]