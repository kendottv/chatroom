from django.urls import re_path
from .consumer import GeminiChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/gemini/chat/$", GeminiChatConsumer.as_asgi()),
]