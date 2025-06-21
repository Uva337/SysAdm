import os
import openai
from PyQt5.QtWidgets import (QAction, QDialog, QVBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QHBoxLayout)
from PyQt5.QtGui import QIcon

from plugin_api import PluginBase


class OpenAIClient:
    """Simple wrapper around the OpenAI chat API."""

    def __init__(self, api_key: str):
        openai.api_key = api_key

    def ask(self, prompt: str) -> str:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message["content"].strip()


class ChatDialog(QDialog):
    def __init__(self, api_client: OpenAIClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setWindowTitle("AI Chat")
        layout = QVBoxLayout(self)

        self.display = QTextEdit(readOnly=True)
        layout.addWidget(self.display)

        input_layout = QHBoxLayout()
        self.input = QLineEdit()
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.on_send)
        input_layout.addWidget(self.input)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)

    def append(self, author: str, text: str):
        self.display.append(f"<b>{author}:</b> {text}")

    def on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.append("You", text)
        self.input.clear()
        try:
            answer = self.api_client.ask(text)
            self.append("Bot", answer)
        except Exception as e:
            self.append("Error", str(e))


class ChatAIPlugin(PluginBase):
    """Plugin providing an AI chat window using OpenAI's API."""

    def __init__(self, app_context=None):
        super().__init__(app_context)
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAIClient(api_key)
        self.dialog = None
        self.action = None

    def activate(self):
        main_window = self.app_context
        self.action = QAction(QIcon.fromTheme("mail-message-new"), "AI Chat", main_window)
        self.action.triggered.connect(self.show_dialog)
        if hasattr(main_window, "tools_menu"):
            main_window.tools_menu.addAction(self.action)

    def show_dialog(self):
        if self.dialog is None:
            self.dialog = ChatDialog(self.client, self.app_context)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def deactivate(self):
        if self.action and hasattr(self.app_context, "tools_menu"):
            self.app_context.tools_menu.removeAction(self.action)
        if self.dialog:
            self.dialog.close()
            self.dialog = None


