"""AI-powered chat page."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation
import platform
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QInputDialog,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QGroupBox,
    QGraphicsOpacityEffect,
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

class _CmdThread(QThread):
    """Run a system command in the background."""

    finished = pyqtSignal(str)

    def __init__(self, cmd: list[str]) -> None:
        super().__init__()
        self.cmd = cmd

    def run(self) -> None:  # pragma: no cover - system dependent
        import subprocess

        encoding = "utf-8"
        if platform.system() == "Windows":
            encoding = "cp866"
        try:
            out = subprocess.run(
                self.cmd,
                capture_output=True,
                text=True,
                encoding=encoding,
                errors="replace",
                check=False,
            )
            msg = out.stdout or out.stderr
        except Exception as exc:  # pragma: no cover - system dependent
            msg = str(exc)
        self.finished.emit(msg)

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

        # Command runner
        cmd_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_run = QPushButton("Run")
        cmd_layout.addWidget(self.cmd_input)
        cmd_layout.addWidget(self.cmd_run)
        right.addLayout(cmd_layout)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        right.addWidget(self.output)

        # Assistant chat
        chat_box = QGroupBox("Assistant")
        chat_layout = QVBoxLayout(chat_box)
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        chat_layout.addWidget(self.history)
        chat_in_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type your message...")
        self.send_btn = QPushButton("Send")
        chat_in_layout.addWidget(self.input)
        chat_in_layout.addWidget(self.send_btn)
        chat_layout.addLayout(chat_in_layout)
        right.addWidget(chat_box)

        self._threads: list[QThread] = []
        self._anim: QPropertyAnimation | None = None

        self.cmd_run.clicked.connect(self._run_cmd)
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
        self._fade(self.history)
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
        self._fade(self.history)

    def _run_cmd(self) -> None:
        """Execute command from the input field."""
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self.cmd_input.clear()
        thread = _CmdThread(cmd.split())
        thread.finished.connect(self._show_output)
        thread.finished.connect(lambda: self._threads.remove(thread))
        self._threads.append(thread)
        thread.start()

    def _show_output(self, text: str) -> None:
        self.output.append(text)
        self._fade(self.output)

    def _fade(self, widget: QWidget) -> None:
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        self._anim = anim
        anim.start()

    # ------------------------------------------------------------------
    def _populate_tree(self) -> None:
        """Load command descriptions into the tree for the selected OS."""
        path = Path(__file__).resolve().parents[1] / "commands.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        os_key = config.os_key()
        self.commands = {}
        categories: dict[str, list[tuple[str, str]]] = {}
        for key, meta in data.items():
            if os_key and os_key not in meta.get("templates", {}):
                continue
            cat = key.split(".")[0].capitalize()
            desc = meta.get("description", key)
            self.commands[key] = meta
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
        """Fill the command input with the selected template."""
        if item.childCount() != 0:
            return
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if not key or key not in self.commands:
            return
        meta = self.commands[key]
        tmpl = meta.get("templates", {}).get(config.os_key())
        if not tmpl:
            QMessageBox.information(self, "Info", "Not supported on this OS")
            return
        params = {}
        for name, pmeta in meta.get("params", {}).items():
            if not pmeta.get("required"):
                continue
            value, ok = QInputDialog.getText(self, "Param", name)
            if not ok or not value:
                return
            params[name] = value
        self.cmd_input.setText(tmpl.format(**params))


