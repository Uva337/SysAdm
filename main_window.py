"""Main window and navigation for SysAdmin Assistant."""
from __future__ import annotations

import sys
from PyQt6.QtCore import Qt, QPropertyAnimation
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
    QSplitter,
    QMenuBar,
    QGraphicsOpacityEffect,
)
from PyQt6.QtGui import QAction

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

        splitter = QSplitter()
        splitter.addWidget(self.nav)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

        self._anim: QPropertyAnimation | None = None

        self._init_menu()

    # Navigation ---------------------------------------------------------
    def _on_nav(self, row: int) -> None:
        text = self.nav.item(row).text() if row >= 0 else ""
        target = {
            "Dashboard": self.dashboard,
            "Chat": self.chat,
            "Installed Apps": self.apps,
            "Functions": self.funcs,
        }.get(text)
        if target:
            self._animate_switch(target)

    def _animate_switch(self, widget: QWidget) -> None:
        """Fade between the current page and ``widget``."""
        current = self.stack.currentWidget()
        if current is widget:
            return
        self.stack.setCurrentWidget(widget)
        for w in (current, widget):
            eff = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(eff)
        fade_out = QPropertyAnimation(current.graphicsEffect(), b"opacity")
        fade_out.setDuration(150)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_in = QPropertyAnimation(widget.graphicsEffect(), b"opacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_out.finished.connect(fade_in.start)
        fade_in.finished.connect(lambda: current.setGraphicsEffect(None))
        fade_in.finished.connect(lambda: widget.setGraphicsEffect(None))
        self._anim = fade_in
        fade_out.start()

    def _init_menu(self) -> None:
        """Create the menu bar with theme options."""
        bar = QMenuBar()
        theme_menu = bar.addMenu("Theme")
        dark_act = QAction("Discord Dark", self)
        light_act = QAction("Light", self)
        theme_menu.addAction(dark_act)
        theme_menu.addAction(light_act)
        dark_act.triggered.connect(lambda: self._apply_theme("dark"))
        light_act.triggered.connect(lambda: self._apply_theme("light"))
        self.setMenuBar(bar)

    def _apply_theme(self, name: str) -> None:
        """Apply the chosen ``name`` theme."""
        config.THEME = name
        app = QApplication.instance()
        if app:
            config.apply_theme(app, name)


def run_app() -> None:
    """Entry point."""
    app = QApplication(sys.argv)
    config.apply_theme(app)

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

