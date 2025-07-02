"""Functions page with command tree and runner."""
from __future__ import annotations

import json
import platform
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QInputDialog,
)

from rapidfuzz import process

import config


class _CmdThread(QThread):
    """Execute a command asynchronously."""

    finished = pyqtSignal(str)

    def __init__(self, cmd: str) -> None:
        super().__init__()
        self.cmd = cmd

    def run(self) -> None:  # pragma: no cover - depends on system
        import subprocess

        enc = "cp866" if platform.system() == "Windows" else "utf-8"
        proc = subprocess.Popen(
            self.cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding=enc,
            errors="replace",
        )
        out, _ = proc.communicate()
        self.finished.emit(out)


class FunctionsPage(QWidget):
    """Display available commands and execute them."""

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)

        self.quick = QListWidget()
        for text in [
            "Ping host",
            "Running processes",
            "Show IP config",
            "Flush DNS",
        ]:
            self.quick.addItem(QListWidgetItem(text))
        layout.addWidget(self.quick)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree)

        right_box = QVBoxLayout()
        self.input = QLineEdit()
        self.run_btn = QPushButton("Run")
        top = QHBoxLayout()
        top.addWidget(self.input)
        top.addWidget(self.run_btn)
        right_box.addLayout(top)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        right_box.addWidget(self.output)
        layout.addLayout(right_box)

        self._threads: list[QThread] = []
        self.quick.itemClicked.connect(self._on_quick)
        self.tree.itemClicked.connect(self._on_tree)
        self.run_btn.clicked.connect(self._on_run)
        self.input.returnPressed.connect(self._on_run)

        self._load_commands()

    # internal helpers --------------------------------------------------
    def _load_commands(self) -> None:
        """Load definitions and build phrase map."""
        path = Path(__file__).resolve().parents[1] / "commands.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return

        os_key = config.os_key()
        self.commands: dict[str, dict] = {}
        self.phrases: dict[str, str] = {}
        categories: dict[str, list[tuple[str, str]]] = {}
        for key, meta in data.items():
            if os_key and os_key not in meta.get("templates", {}):
                continue
            desc = meta.get("description", key)
            self.commands[key] = meta
            for ph in meta.get("phrases", []):
                self.phrases[ph] = key
            cat = key.split(".")[0].capitalize()
            categories.setdefault(cat, []).append((key, desc))
        for cat, items in sorted(categories.items()):
            cat_item = QTreeWidgetItem([cat])
            self.tree.addTopLevelItem(cat_item)
            for key, desc in sorted(items, key=lambda i: i[1]):
                child = QTreeWidgetItem([desc])
                child.setData(0, Qt.ItemDataRole.UserRole, key)
                cat_item.addChild(child)
        self.tree.expandAll()

    def _on_tree(self, item: QTreeWidgetItem) -> None:
        """Show description for selected command."""
        if item.childCount() != 0:
            return
        key = item.data(0, Qt.ItemDataRole.UserRole)
        meta = self.commands.get(key)
        if not meta:
            return
        QMessageBox.information(self, "Info", meta.get("description", key))

    def _on_quick(self, item: QListWidgetItem) -> None:
        """Handle quick command shortcuts."""
        text = item.text()
        if text == "Ping host":
            host, ok = QInputDialog.getText(self, "Ping", "Host")
            if ok and host:
                cmd = "ping -n 4 " + host if platform.system() == "Windows" else f"ping -c 4 {host}"
                self._run_cmd(cmd)
        elif text == "Running processes":
            self._run_cmd("tasklist" if platform.system() == "Windows" else "ps aux")
        elif text == "Show IP config":
            if platform.system() == "Windows":
                cmd = "ipconfig"
            elif platform.system() == "Linux":
                cmd = "ip a"
            else:
                cmd = "ifconfig"
            self._run_cmd(cmd)
        elif text == "Flush DNS":
            if platform.system() == "Windows":
                cmd = "ipconfig /flushdns"
            elif platform.system() == "Linux":
                cmd = "systemd-resolve --flush-caches"
            else:
                cmd = "dscacheutil -flushcache"
            self._run_cmd(cmd)

    def _on_run(self) -> None:
        """Parse natural text and execute a matching command."""
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        match = process.extractOne(text, list(self.phrases.keys()))
        if not match or match[1] < 60:
            QMessageBox.warning(self, "Not found", "Cannot map input to command")
            return
        key = self.phrases[match[0]]
        meta = self.commands.get(key)
        if not meta:
            return
        tmpl = meta.get("templates", {}).get(config.os_key())
        if not tmpl:
            QMessageBox.information(self, "Info", "Not supported on this OS")
            return
        params = {}
        for name, spec in meta.get("params", {}).items():
            if spec.get("required"):
                value, ok = QInputDialog.getText(self, "Param", name)
                if not ok or not value:
                    return
                params[name] = value
        cmd = tmpl.format(**params)
        exe = cmd.split()[0]
        if not shutil.which(exe) and not Path(exe).exists():
            QMessageBox.critical(self, "Executable missing", f"{exe} not found")
            return
        self._run_cmd(cmd)

    def _run_cmd(self, cmd: str) -> None:
        """Run a command and display its output."""
        thread = _CmdThread(cmd)
        thread.finished.connect(self._show_output)
        thread.finished.connect(lambda: self._threads.remove(thread))
        self._threads.append(thread)
        thread.start()

    def _show_output(self, text: str) -> None:
        self.output.append(text)
