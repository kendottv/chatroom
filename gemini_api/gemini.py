# gemini_api/gemini.py (或你的 wrapper 檔案路徑)
import os
from datetime import timedelta
from django.core.cache import cache
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CLIENT = genai.Client(api_key=GOOGLE_API_KEY)

MODEL_ID = "gemini-2.0-flash-001"   # 或你要用的模型
REDIS_EXPIRE_SECONDS = 7200         # 2 小時

def _cache_key(session_key: str) -> str:
    return f"genai_history:{session_key}"

# 把純文字包成 Content（user / model）
def _user_msg(text: str) -> dict:
    # 新 SDK 支援 dict 形式的 Content（TypedDict）
    return {
        "role": "user",
        "parts": [ {"text": text} ]
    }

def _model_msg(text: str) -> dict:
    return {
        "role": "model",
        "parts": [ {"text": text} ]
    }

class GeminiAPIWrapper:
    def __init__(self, session_key: str):
        self.session_key = session_key
        # 1) 從 Redis 讀取你自己維護的歷史（list[dict]）
        self.history = cache.get(_cache_key(session_key)) or []

        # 2) 以現有歷史建立 chat（注意：這裡是**帶入**，不是去讀 chat.history）
        #    history 可直接給 dict 形式（SDK 會轉型）
        self.chat = CLIENT.chats.create(
            model=MODEL_ID,
            # 如需 system 指令或其它參數，可放到 config
            # config=types.GenerateContentConfig(system_instruction="..."),
            history=self.history
        )

    async def async_get_response(self, prompt: str) -> str:
        """
        取完整結果（非串流）。你原本 ask_ai 就是 await 這個。
        """
        # 新 SDK 的 chat 是同步方法；在 async context 用 thread 包
        import asyncio
        response = await asyncio.to_thread(self.chat.send_message, prompt)
        text = response.text or ""

        # 3) 由你**自己**把新輪對話寫回 self.history（user + model）
        self.history.append(_user_msg(prompt))
        self.history.append(_model_msg(text))

        # 4) 存回 Redis，續命 2 小時
        cache.set(_cache_key(self.session_key), self.history, REDIS_EXPIRE_SECONDS)
        return text

    def stream_response(self, prompt: str):
        """
        如果你要同步串流（給 StreamingHttpResponse 用），也一樣自己維護歷史。
        """
        for chunk in self.chat.send_message_stream(prompt):
            if chunk.text:
                yield chunk.text

        # 串流結束後再一次性更新歷史與快取
        # （這裡用最後整段輸出；如需逐塊累積可自行改）
        final_text = getattr(self.chat, "last_text", None) or ""
        self.history.append(_user_msg(prompt))
        self.history.append(_model_msg(final_text))
        cache.set(_cache_key(self.session_key), self.history, REDIS_EXPIRE_SECONDS)