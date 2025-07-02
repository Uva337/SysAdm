"""Main window and navigation for SysAdmin Assistant."""
from __future__ import annotations

import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QHBoxLayout,
    QWidget,
    QMessageBox,
    QDialog,
)

import config
from config import APP_STATE
from dialogs.login import LoginDialog
from dialogs.os_select import OSSelectDialog
from pages.chat_page import ChatPage
from pages.dashboard import DashboardPage
from pages.app_manager import AppManagerPage
from pages.functions_page import FunctionsPage



class MainWindow(QMainWindow):
    """Application main window with page navigation."""

    def __init__(self) -> None:
        """Initialize navigation and pages."""
        super().__init__()
        self.setWindowTitle("SysAdmin Assistant")
        self.resize(900, 600)

        self.nav = QListWidget()
        for text in ["Dashboard", "Installed Apps", "Functions", "Chat"]:
            self.nav.addItem(QListWidgetItem(text))
        self.nav.currentRowChanged.connect(self._on_nav)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage()
        self.chat = ChatPage()
        self.apps = AppManagerPage()
        self.funcs = FunctionsPage()
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.chat)
        self.stack.addWidget(self.apps)
        self.stack.addWidget(self.funcs)

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
        elif text == "Installed Apps":
            self.stack.setCurrentWidget(self.apps)
        elif text == "Functions":
            self.stack.setCurrentWidget(self.funcs)


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

