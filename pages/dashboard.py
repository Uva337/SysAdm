"""Live system monitoring dashboard."""
from __future__ import annotations

import psutil
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
)


class DashboardPage(QWidget):
    """Shows CPU, RAM stats and top memory-consuming processes."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        grid = QGridLayout()
        layout.addLayout(grid)

        self.cpu_label = QLabel()
        self.freq_label = QLabel()
        self.ram_label = QLabel()
        self.net_label = QLabel()
        self.disk_label = QLabel()
        grid.addWidget(QLabel("CPU %"), 0, 0)
        grid.addWidget(self.cpu_label, 0, 1)
        grid.addWidget(QLabel("Frequency"), 1, 0)
        grid.addWidget(self.freq_label, 1, 1)
        grid.addWidget(QLabel("RAM"), 2, 0)
        grid.addWidget(self.ram_label, 2, 1)
        grid.addWidget(QLabel("Network I/O"), 3, 0)
        grid.addWidget(self.net_label, 3, 1)
        grid.addWidget(QLabel("Disk usage"), 4, 0)
        grid.addWidget(self.disk_label, 4, 1)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["PID", "Name", "RAM MB"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stats)

    # QWidget events -----------------------------------------------------
    def showEvent(self, event) -> None:  # type: ignore[override]
        self._timer.start(2000)
        super().showEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    def _update_stats(self) -> None:
        self.cpu_label.setText(f"{psutil.cpu_percent():.0f}%")
        freqs = psutil.cpu_freq(percpu=True)
        if freqs:
            self.freq_label.setText(", ".join(f"{f.current:.0f}MHz" for f in freqs))
        mem = psutil.virtual_memory()
        self.ram_label.setText(
            f"{mem.used // (1024 ** 2)} / {mem.total // (1024 ** 2)} MB"
        )
        net = psutil.net_io_counters()
        self.net_label.setText(
            f"{net.bytes_sent // (1024 ** 2)}MB up / {net.bytes_recv // (1024 ** 2)}MB down"
        )
        disk = psutil.disk_usage('/')
        self.disk_label.setText(f"{disk.percent}%")
        processes = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                rss = proc.info["memory_info"].rss // (1024 ** 2)
                processes.append((rss, proc.info["pid"], proc.info["name"]))
            except Exception:
                continue
        processes.sort(reverse=True)
        top = processes[:8]
        self.table.setRowCount(len(top))
        for row, (rss, pid, name) in enumerate(top):
            self.table.setItem(row, 0, QTableWidgetItem(str(pid)))
            self.table.setItem(row, 1, QTableWidgetItem(name))
            self.table.setItem(row, 2, QTableWidgetItem(str(rss)))

