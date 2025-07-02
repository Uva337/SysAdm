# main_window.py
"""Main application window and onboarding flow using PyQt6."""

from __future__ import annotations

import os
import platform
from typing import List, Dict

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QTextEdit, QLineEdit,
    QPushButton, QLabel, QMessageBox, QDialog, QDialogButtonBox,
    QComboBox, QFormLayout, QGroupBox, QGridLayout, QTableWidget,
    QTableWidgetItem, QCheckBox, QProgressDialog
)

import psutil

from auth_rbac import AuthManager, Role
import app_manager


class DeepSeekChatPlugin:
    """Simple stub for DeepSeek chat interaction."""

    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")

    def chat(self, message: str) -> str:
        if not self.api_key:
            raise RuntimeError("Missing API key")
        # Placeholder implementation
        return f"Echo: {message}"


class LoginDialog(QDialog):
    """Login form that uses AuthManager for verification."""

    def __init__(self, auth: AuthManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth = auth
        self.username: str = ""
        self.role: Role | None = None
        self.setWindowTitle("Sign in")
        layout = QFormLayout(self)

        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addRow("Username", self.user_edit)
        layout.addRow("Password", self.pass_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._handle_login)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _handle_login(self) -> None:
        user = self.user_edit.text().strip()
        pwd = self.pass_edit.text()
        role = self._auth.verify_user(user, pwd)
        if role:
            self.username = user
            self.role = role
            self.accept()
        else:
            QMessageBox.warning(self, "Login failed", "Invalid username or password")


class OSSelectionDialog(QDialog):
    """Dialog to choose target operating system."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.os_name = platform.system()
        self.setWindowTitle("Choose OS")
        layout = QVBoxLayout(self)
        self.combo = QComboBox()
        self.combo.addItems(["Windows", "Linux", "macOS"])
        index = self.combo.findText(self.os_name)
        if index >= 0:
            self.combo.setCurrentIndex(index)
        layout.addWidget(self.combo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.os_name = self.combo.currentText()
        self.accept()


class WorkerThread(QThread):
    """Runs an app operation in a background thread."""

    progress = pyqtSignal(int)

    def __init__(self, func, packages: List[str], os_name: str) -> None:
        super().__init__()
        self.func = func
        self.packages = packages
        self.os_name = os_name

    def run(self) -> None:
        for i, name in enumerate(self.packages, 1):
            try:
                self.func(name, self.os_name)
            except Exception:
                pass
            self.progress.emit(i)


class MainWindow(QMainWindow):
    """Main application window with navigation."""

    def __init__(self, username: str, role: Role, os_name: str) -> None:
        super().__init__()
        self.username = username
        self.role = role
        self.os_name = os_name
        self.chat_plugin = DeepSeekChatPlugin()

        self.setWindowTitle("SysAdmin Assistant")
        self.resize(1000, 700)

        self.nav_list = QListWidget()
        for name in ["Dashboard", "Chat", "Apps"]:
            item = QListWidgetItem(name)
            item.setFont(QFont("Segoe UI", 11))
            self.nav_list.addItem(item)
        self.nav_list.currentRowChanged.connect(self._set_page)

        self.stack = QStackedWidget()
        self.dashboard_page = self._create_dashboard_page()
        self.chat_page = self._create_chat_page()
        self.apps_page = self._create_apps_page()
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.chat_page)
        self.stack.addWidget(self.apps_page)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.nav_list)
        main_layout.addWidget(self.stack)

        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        self.dashboard_timer = QTimer(self)
        self.dashboard_timer.timeout.connect(self._update_dashboard)

    # --- Navigation -----------------------------------------------------
    def _set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    # --- Chat page ------------------------------------------------------
    def _create_chat_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_input = QLineEdit()
        send_btn = QPushButton("Send")
        send_layout = QHBoxLayout()
        send_layout.addWidget(self.chat_input)
        send_layout.addWidget(send_btn)
        layout.addWidget(self.chat_history)
        layout.addLayout(send_layout)

        def send() -> None:
            text = self.chat_input.text().strip()
            if not text:
                return
            self.chat_history.append(f"You: {text}")
            self.chat_input.clear()
            try:
                answer = self.chat_plugin.chat(text)
            except Exception as exc:  # pragma: no cover - GUI message
                if "Missing API key" in str(exc):
                    QMessageBox.warning(
                        self,
                        "Missing API key",
                        "Set DEEPSEEK_API_KEY environment variable to use chat.",
                    )
                    return
                QMessageBox.warning(self, "Chat error", str(exc))
                return
            self.chat_history.append(f"AI: {answer}")

        send_btn.clicked.connect(send)
        self.chat_input.returnPressed.connect(send)
        return page

    # --- Dashboard ------------------------------------------------------
    def _create_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        info = QGroupBox("System")
        info_layout = QFormLayout(info)
        info_layout.addRow("Host", QLabel(platform.node()))
        info_layout.addRow("OS", QLabel(platform.platform()))
        layout.addWidget(info)

        self.stats_group = QGroupBox("Live stats")
        stats = QGridLayout(self.stats_group)
        self.cpu_label = QLabel()
        self.freq_label = QLabel()
        self.ram_label = QLabel()
        stats.addWidget(QLabel("CPU usage"), 0, 0)
        stats.addWidget(self.cpu_label, 0, 1)
        stats.addWidget(QLabel("Frequency"), 1, 0)
        stats.addWidget(self.freq_label, 1, 1)
        stats.addWidget(QLabel("RAM"), 2, 0)
        stats.addWidget(self.ram_label, 2, 1)

        self.proc_table = QTableWidget(0, 3)
        self.proc_table.setHorizontalHeaderLabels(["PID", "Name", "RSS MB"])
        self.proc_table.horizontalHeader().setStretchLastSection(True)
        stats.addWidget(self.proc_table, 3, 0, 1, 2)
        layout.addWidget(self.stats_group)
        return page

    def _update_dashboard(self) -> None:
        cpu = psutil.cpu_percent()
        self.cpu_label.setText(f"{cpu:.0f}%")
        freqs = psutil.cpu_freq(percpu=True)
        if freqs:
            self.freq_label.setText(", ".join(f"{f.current:.0f}MHz" for f in freqs))
        mem = psutil.virtual_memory()
        self.ram_label.setText(
            f"{mem.used // (1024 ** 2)} MB / {mem.total // (1024 ** 2)} MB"
        )
        processes = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                rss = proc.info["memory_info"].rss // (1024 ** 2)
                processes.append((rss, proc.info["pid"], proc.info["name"]))
            except Exception:
                continue
        processes.sort(reverse=True)
        top = processes[:5]
        self.proc_table.setRowCount(len(top))
        for row, (rss, pid, name) in enumerate(top):
            self.proc_table.setItem(row, 0, QTableWidgetItem(str(pid)))
            self.proc_table.setItem(row, 1, QTableWidgetItem(name))
            self.proc_table.setItem(row, 2, QTableWidgetItem(str(rss)))

    # --- Apps page ------------------------------------------------------
    def _create_apps_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.apps_table = QTableWidget(0, 3)
        self.apps_table.setHorizontalHeaderLabels([
            "Name",
            "Version",
            "Install Date",
        ])
        self.apps_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.apps_table)

        tools_group = QGroupBox("Recommended tools")
        tools_layout = QVBoxLayout(tools_group)
        self.tools: Dict[str, QCheckBox] = {}
        for tool in ["CryptoPro", "Trassir", "Git"]:
            cb = QCheckBox(tool)
            self.tools[tool] = cb
            tools_layout.addWidget(cb)
        layout.addWidget(tools_group)

        btn_layout = QHBoxLayout()
        install_btn = QPushButton("Install")
        remove_btn = QPushButton("Remove")
        btn_layout.addWidget(install_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)

        install_btn.clicked.connect(lambda: self._run_app_task(app_manager.install_app))
        remove_btn.clicked.connect(lambda: self._run_app_task(app_manager.uninstall_app))

        self._refresh_apps()
        return page

    def _refresh_apps(self) -> None:
        packages = app_manager.get_installed_packages(self.os_name)
        self.apps_table.setRowCount(len(packages))
        for row, pkg in enumerate(packages):
            self.apps_table.setItem(row, 0, QTableWidgetItem(pkg.get("name", "")))
            self.apps_table.setItem(row, 1, QTableWidgetItem(pkg.get("version", "")))
            self.apps_table.setItem(row, 2, QTableWidgetItem(pkg.get("date", "")))
        self.apps_table.resizeColumnsToContents()

    def _run_app_task(self, func) -> None:
        selected = [name for name, cb in self.tools.items() if cb.isChecked()]
        if not selected:
            return

        dialog = QProgressDialog("Working...", "Cancel", 0, len(selected), self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        thread = WorkerThread(func, selected, self.os_name)
        thread.progress.connect(dialog.setValue)
        thread.finished.connect(lambda: (dialog.close(), self._refresh_apps()))
        thread.start()
        dialog.exec()

    # ------------------------------------------------------------------
    def showEvent(self, event) -> None:  # type: ignore[override]
        self.dashboard_timer.start(2000)
        super().showEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.dashboard_timer.isActive():
            self.dashboard_timer.stop()
        super().closeEvent(event)


def run_app() -> None:
    """Application entry point."""

    app = QApplication([])
    auth = AuthManager()

    login = LoginDialog(auth)
    if login.exec() != QDialog.DialogCode.Accepted:
        return

    os_dialog = OSSelectionDialog()
    if os_dialog.exec() != QDialog.DialogCode.Accepted:
        return

    window = MainWindow(login.username, login.role or Role.OPERATOR, os_dialog.os_name)
    window.show()
    app.exec()


if __name__ == "__main__":
    run_app()
