from plugin_api import PluginBase
import os
import json
import urllib.request

class DeepSeekChatPlugin(PluginBase):
    def __init__(self, api_key=None, app_context=None):
        super().__init__(app_context)
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")

    def activate(self):
        pass

    def deactivate(self):
        pass

    def chat(self, message: str) -> str:
        if not self.api_key:
            raise RuntimeError("Отсутствует API ключ DeepSeek")
        url = "https://api.deepseek.com/v1/chat/completions"
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": message}
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )
        try:
            with urllib.request.urlopen(req) as resp:
                resp_data = resp.read().decode("utf-8")
                res_json = json.loads(resp_data)
                return res_json.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            raise RuntimeError(f"Ошибка запроса: {e}")
