"""Operating system selection dialog."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
)


class OSSelectDialog(QDialog):
    """Allows user to choose target operating system."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.os_name = "Windows"
        self.setWindowTitle("Select OS")
        layout = QVBoxLayout(self)

        self.combo = QComboBox()
        self.combo.addItems(["Windows", "Linux", "macOS"])
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

