"""Simple login dialog with stub authentication."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
)


class LoginDialog(QDialog):
    """Username/password login form."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Login")
        layout = QFormLayout(self)

        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addRow("Username", self.user_edit)
        layout.addRow("Password", self.pass_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._check_login)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _check_login(self) -> None:
        if (
            self.user_edit.text().strip() == "admin"
            and self.pass_edit.text() == "password"
        ):
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")

