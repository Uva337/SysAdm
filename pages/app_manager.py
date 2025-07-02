"""Page for managing installed applications."""
from __future__ import annotations

from typing import Dict, List

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    QProgressDialog,
)

import helpers.os_tools as os_tools
import config


class _WorkerThread(QThread):
    progress = pyqtSignal(int)

    def __init__(self, func, packages: List[str], os_name: str) -> None:
        super().__init__()
        self.func = func
        self.packages = packages
        self.os_name = os_name

    def run(self) -> None:  # pragma: no cover - GUI thread
        for i, pkg in enumerate(self.packages, 1):
            try:
                self.func(pkg, self.os_name)
            except Exception:
                pass
            self.progress.emit(i)


class AppManagerPage(QWidget):
    """Displays installed packages and manages recommended tools."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Version", "Install Date"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        group = QGroupBox("Recommended tools")
        g_layout = QVBoxLayout(group)
        self.tools: Dict[str, QCheckBox] = {}
        for name in ["CryptoPro", "Trassir", "Wireshark", "PuTTY", "7-Zip"]:
            cb = QCheckBox(name)
            self.tools[name] = cb
            g_layout.addWidget(cb)
        layout.addWidget(group)

        btn_layout = QHBoxLayout()
        install_btn = QPushButton("Install Selected")
        remove_btn = QPushButton("Remove Selected")
        btn_layout.addWidget(install_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)

        install_btn.clicked.connect(lambda: self._run_task(os_tools.install_app))
        remove_btn.clicked.connect(lambda: self._run_task(os_tools.uninstall_app))

        self._refresh()

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        packages = os_tools.get_installed_packages(config.APP_STATE.current_os or "")
        self.table.setRowCount(len(packages))
        for row, pkg in enumerate(packages):
            self.table.setItem(row, 0, QTableWidgetItem(pkg.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(pkg.get("version", "")))
            self.table.setItem(row, 2, QTableWidgetItem(pkg.get("date", "")))
        self.table.resizeColumnsToContents()

    def _run_task(self, func) -> None:
        selected = [name for name, cb in self.tools.items() if cb.isChecked()]
        if not selected:
            return
        dialog = QProgressDialog("Working...", "Cancel", 0, len(selected), self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

        thread = _WorkerThread(func, selected, config.APP_STATE.current_os or "")
        thread.progress.connect(dialog.setValue)
        thread.finished.connect(lambda: (dialog.close(), self._refresh()))
        thread.start()
        dialog.exec()

