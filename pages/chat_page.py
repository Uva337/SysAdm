"""AI-powered chat page."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)

try:
    from deepseek import DeepSeekChatPlugin
except ImportError:  # pragma: no cover - fallback for older package
    from deepseek import DeepSeekAPI

    class DeepSeekChatPlugin:
        """Simple wrapper around :class:`DeepSeekAPI`."""

        def __init__(self, api_key: str) -> None:
            self._api = DeepSeekAPI(api_key=api_key)

        def chat(self, message: str) -> str:
            """Return a completion for ``message``."""
            return self._api.chat_completion(prompt=message)

import config


class ChatPage(QWidget):
    """Page allowing user to chat with DeepSeek AI."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        layout.addWidget(self.history)

        input_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.send_btn = QPushButton("Send")
        input_layout.addWidget(self.input)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        self.send_btn.clicked.connect(self._send)
        self.input.returnPressed.connect(self._send)

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        if not config.DEEPSEEK_API_KEY:
            QMessageBox.critical(
                self,
                "Missing API key",
                "\u0423\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435 \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u0443\u044e \u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\u044f DEEPSEEK_API_KEY \u0438\u043b\u0438 .env \u0444\u0430\u0439\u043b"
            )
            return
        plugin = DeepSeekChatPlugin(api_key=config.DEEPSEEK_API_KEY)
        self.history.append(f"You: {text}")
        self.input.clear()
        try:
            reply = plugin.chat(text)
        except Exception as exc:  # pragma: no cover - network errors
            QMessageBox.warning(self, "Chat error", str(exc))
            return
        self.history.append(f"AI: {reply}")
        self.history.verticalScrollBar().setValue(
            self.history.verticalScrollBar().maximum()
        )

