import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .gemini import GeminiAPIWrapper


class GeminiChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_key = self.scope["session"].session_key
        if not self.session_key:
            await self.scope["session"].save()
            self.session_key = self.scope["session"].session_key

        await self.accept()
        await self.send(json.dumps({"type": "info", "message": "WebSocket connected."}))

    async def disconnect(self, close_code):
        pass  # 可釋放資源

    async def receive(self, text_data):
        data = json.loads(text_data)
        prompt = data.get("prompt")

        if not prompt:
            await self.send(json.dumps({"type": "error", "message": "缺少 prompt"}))
            return

        wrapper = GeminiAPIWrapper(self.session_key)

        await self.send(json.dumps({"type": "start"}))

        async for chunk in wrapper.async_stream_response(prompt):
            await self.send(json.dumps({
                "type": "chunk",
                "data": chunk
            }))

        await self.send(json.dumps({"type": "done"}))