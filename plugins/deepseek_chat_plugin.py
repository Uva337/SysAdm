from plugin_api import PluginBase
import os
import requests

class DeepSeekChatPlugin(PluginBase):
    """Plugin that provides chat interaction via DeepSeek API."""

    def activate(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            print("DEEPSEEK_API_KEY not set. DeepSeekChatPlugin disabled.")
        else:
            print("DeepSeekChatPlugin activated.")

    def deactivate(self):
        print("DeepSeekChatPlugin deactivated.")

    def chat(self, messages, model="deepseek-chat", temperature=0.7):
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not configured")
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
