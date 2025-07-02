"""Main window and navigation for SysAdmin Assistant."""
from __future__ import annotations

import sys
import subprocess
import platform

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QHBoxLayout,
    QWidget,
    QMessageBox,
    QInputDialog,
    QDialog,
)

import config
from config import APP_STATE
from dialogs.login import LoginDialog
from dialogs.os_select import OSSelectDialog
from pages.chat_page import ChatPage
from pages.dashboard import DashboardPage
from pages.app_manager import AppManagerPage
import psutil


class _CmdThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, cmd: list[str]) -> None:
        super().__init__()
        self.cmd = cmd

    def run(self) -> None:  # pragma: no cover - depends on system
        try:
            out = subprocess.run(self.cmd, capture_output=True, text=True, check=False)
            msg = out.stdout or out.stderr
        except Exception as exc:  # pragma: no cover - system dependent
            msg = str(exc)
        self.finished.emit(msg)


class MainWindow(QMainWindow):
    """Application main window with page navigation."""

    def __init__(self) -> None:
        """Initialize navigation and pages."""
        super().__init__()
        self.setWindowTitle("SysAdmin Assistant")
        self.resize(900, 600)

        self.nav = QListWidget()
        items = [
            "Dashboard",
            "Chat",
            "Apps",
            "----------",
            "Ping host",
            "Running processes",
            "Show IP config",
            "Flush DNS",
        ]
        for text in items:
            item = QListWidgetItem(text)
            if text == "----------":
                item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._on_nav)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage()
        self.chat = ChatPage()
        self.apps = AppManagerPage()
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.chat)
        self.stack.addWidget(self.apps)

        self._threads: list[QThread] = []

        layout = QHBoxLayout()
        layout.addWidget(self.nav)
        layout.addWidget(self.stack)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    # Navigation ---------------------------------------------------------
    def _on_nav(self, row: int) -> None:
        text = self.nav.item(row).text() if row >= 0 else ""
        if text == "Dashboard":
            self.stack.setCurrentWidget(self.dashboard)
        elif text == "Chat":
            self.stack.setCurrentWidget(self.chat)
        elif text == "Apps":
            self.stack.setCurrentWidget(self.apps)
        elif text == "Ping host":
            host, ok = QInputDialog.getText(self, "Ping", "Host")
            if ok and host:
                cmd = ["ping", host] if platform.system() == "Windows" else ["ping", "-c", "4", host]
                self._run_cmd(cmd)
        elif text == "Running processes":
            out = "\n".join(f"{p.pid} {p.name()}" for p in psutil.process_iter())
            self._show_output(out)
        elif text == "Show IP config":
            if platform.system() == "Windows":
                cmd = ["ipconfig"]
            elif platform.system() == "Linux":
                cmd = ["ip", "a"]
            elif platform.system() == "Darwin":
                cmd = ["ifconfig"]
            else:
                self._toast("\u041d\u0435 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u0442\u0441\u044f")
                return
            self._run_cmd(cmd)
        elif text == "Flush DNS":
            if platform.system() == "Windows":
                cmd = ["ipconfig", "/flushdns"]
            elif platform.system() == "Linux":
                cmd = ["systemd-resolve", "--flush-caches"]
            elif platform.system() == "Darwin":
                cmd = ["dscacheutil", "-flushcache"]
            else:
                self._toast("\u041d\u0435 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u0442\u0441\u044f")
                return
            self._run_cmd(cmd)

    def _run_cmd(self, cmd: list[str]) -> None:
        """Run a system command in a background thread."""
        thread = _CmdThread(cmd)
        thread.finished.connect(self._show_output)
        thread.finished.connect(lambda: self._threads.remove(thread))
        self._threads.append(thread)
        thread.start()

    def _show_output(self, text: str) -> None:
        """Show command output in a message box."""
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Output")
        dlg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dlg.setText(text)
        dlg.exec()

    def _toast(self, text: str) -> None:
        """Display a short informational message."""
        QMessageBox.information(self, "Info", text)


def run_app() -> None:
    """Entry point."""
    app = QApplication(sys.argv)
    try:
        with open("resources/styles.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception:
        pass

    if not config.DEEPSEEK_API_KEY:
        QMessageBox.critical(
            None,
            "Missing API key",
            "\u0423\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435 DEEPSEEK_API_KEY \u0432 .env \u0438\u043b\u0438 \u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\u0438",
        )

    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        return

    os_dialog = OSSelectDialog()
    if os_dialog.exec() != QDialog.DialogCode.Accepted:
        return

    APP_STATE.current_os = os_dialog.os_name

    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run_app()

