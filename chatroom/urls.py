"""
URL configuration for chatroom project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from room import views

app_name = 'room'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),  # 首頁
    path('exam/', views.exam, name='exam'),  # 考試頁（做題）
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
]

# 僅在 DEBUG 模式下服務靜態文件和媒體文件
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)