"""AI-powered chat page."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
)

try:  # pragma: no cover - package may be absent on CI
    from deepseek import DeepSeekChatPlugin
except Exception:  # Module missing or outdated
    try:  # legacy API
        from deepseek import DeepSeekAPI  # type: ignore
    except Exception:  # completely missing
        DeepSeekAPI = None  # type: ignore

    class DeepSeekChatPlugin:  # pragma: no cover - minimal fallback
        """Fallback wrapper around :class:`DeepSeekAPI`."""

        def __init__(self, api_key: str) -> None:
            if DeepSeekAPI is None:
                raise RuntimeError(
                    "DeepSeek package is not installed"
                )
            self._api = DeepSeekAPI(api_key=api_key)

        def chat(self, message: str) -> str:
            """Return a completion for ``message``."""
            return self._api.chat_completion(prompt=message)

import config
import json
from pathlib import Path


class ChatPage(QWidget):
    """Page allowing user to chat with DeepSeek AI."""

    def __init__(self) -> None:
        """Initialize widgets for chat history and input."""
        super().__init__()
        layout = QHBoxLayout(self)

        splitter = QSplitter()
        layout.addWidget(splitter)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        splitter.addWidget(self.tree)

        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([200, 600])

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        right.addWidget(self.history)

        input_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type your message...")
        self.send_btn = QPushButton("Send")
        input_layout.addWidget(self.input)
        input_layout.addWidget(self.send_btn)
        right.addLayout(input_layout)

        self.send_btn.clicked.connect(self._send)
        self.input.returnPressed.connect(self._send)
        self.tree.itemClicked.connect(self._on_item)

        self._populate_tree()

    def _send(self) -> None:
        """Handle sending a message to DeepSeek and display the reply."""
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
            msg = str(exc)
            if "402" in msg or "Insufficient" in msg:
                msg = (
                    "Your DeepSeek account has insufficient balance. "
                    "Please top up your credits."
                )
            QMessageBox.warning(self, "Chat error", msg)
            return
        self.history.append(f"AI: {reply}")
        self.history.verticalScrollBar().setValue(
            self.history.verticalScrollBar().maximum()
        )

    # ------------------------------------------------------------------
    def _populate_tree(self) -> None:
        """Load command descriptions into the tree."""
        path = Path("commands.json")
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        categories: dict[str, list[tuple[str, str]]] = {}
        for key, meta in data.items():
            cat = key.split(".")[0].capitalize()
            desc = meta.get("description", key)
            categories.setdefault(cat, []).append((key, desc))
        for cat, items in sorted(categories.items()):
            cat_item = QTreeWidgetItem([cat])
            self.tree.addTopLevelItem(cat_item)
            for key, desc in sorted(items, key=lambda p: p[1]):
                child = QTreeWidgetItem([desc])
                child.setData(0, Qt.ItemDataRole.UserRole, key)
                cat_item.addChild(child)
        self.tree.expandAll()

    def _on_item(self, item: QTreeWidgetItem) -> None:
        """Insert clicked command description into the input field."""
        if item.childCount() == 0:
            self.input.setText(item.text(0))

