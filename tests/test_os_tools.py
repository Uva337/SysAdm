import sys
import pathlib
import subprocess
from typing import List

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import helpers.os_tools as os_tools


class DummyCompleted:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout


def test_get_installed_packages_linux(monkeypatch):
    def fake_run(cmd, capture_output=True, text=True, check=False):
        return DummyCompleted("header\n" * 5 + "ii testpkg 1.0 amd64 desc\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    packages = os_tools.get_installed_packages("Linux")
    assert packages == [{"name": "testpkg", "version": "1.0", "date": ""}]


def test_install_uninstall(monkeypatch):
    called: List[List[str]] = []

    def fake_run(cmd, check=False):
        called.append(cmd)
        return DummyCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)
    os_tools.install_app("foo", "Linux")
    os_tools.uninstall_app("foo", "Linux")
    assert called == [
        ["sudo", "apt-get", "-y", "install", "foo"],
        ["sudo", "apt-get", "-y", "remove", "foo"],
    ]

