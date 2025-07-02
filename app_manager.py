# app_manager.py
"""Utilities for managing system applications."""

from __future__ import annotations

import platform
import subprocess
from typing import List, Dict

try:
    import winreg
except ImportError:  # pragma: no cover - non windows
    winreg = None


def get_installed_packages(os_name: str) -> List[Dict[str, str]]:
    """Return installed packages list for the given OS."""
    packages: List[Dict[str, str]] = []
    os_lower = os_name.lower()
    try:
        if os_lower == "windows" and winreg:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            for i in range(winreg.QueryInfoKey(root)[0]):
                sub = winreg.EnumKey(root, i)
                subkey = winreg.OpenKey(root, sub)
                name = _safe_reg_value(subkey, "DisplayName")
                if not name:
                    continue
                packages.append({
                    "name": name,
                    "version": _safe_reg_value(subkey, "DisplayVersion"),
                    "date": _safe_reg_value(subkey, "InstallDate"),
                })
        elif os_lower in {"debian", "ubuntu"}:
            out = subprocess.run(["dpkg", "--list"], capture_output=True, text=True, check=False).stdout
            for line in out.splitlines()[5:]:
                parts = line.split()
                if len(parts) >= 5:
                    packages.append({"name": parts[1], "version": parts[2], "date": ""})
        elif os_lower in {"rhel", "fedora"}:
            out = subprocess.run([
                "rpm",
                "-qa",
                "--qf",
                "%{NAME} %{VERSION} %{INSTALLTIME:date}\n",
            ], capture_output=True, text=True, check=False).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    packages.append({"name": parts[0], "version": parts[1], "date": " ".join(parts[2:])})
        elif os_lower == "macos":
            out = subprocess.run(["brew", "list", "--versions"], capture_output=True, text=True, check=False).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    packages.append({"name": parts[0], "version": parts[1], "date": ""})
    except Exception:
        pass
    return packages


def install_app(name: str, os_name: str) -> None:
    """Install a package by name."""
    os_lower = os_name.lower()
    if os_lower == "windows":
        subprocess.run(["winget", "install", "-e", "--id", name], check=False)
    elif os_lower in {"debian", "ubuntu"}:
        subprocess.run(["sudo", "apt-get", "-y", "install", name], check=False)
    elif os_lower in {"rhel", "fedora"}:
        subprocess.run(["sudo", "yum", "-y", "install", name], check=False)
    elif os_lower == "macos":
        subprocess.run(["brew", "install", name], check=False)


def uninstall_app(name: str, os_name: str) -> None:
    """Remove a package by name."""
    os_lower = os_name.lower()
    if os_lower == "windows":
        subprocess.run(["winget", "uninstall", "-e", "--id", name], check=False)
    elif os_lower in {"debian", "ubuntu"}:
        subprocess.run(["sudo", "apt-get", "-y", "remove", name], check=False)
    elif os_lower in {"rhel", "fedora"}:
        subprocess.run(["sudo", "yum", "-y", "remove", name], check=False)
    elif os_lower == "macos":
        subprocess.run(["brew", "uninstall", name], check=False)


def _safe_reg_value(key, name: str) -> str:
    try:
        return winreg.QueryValueEx(key, name)[0]
    except Exception:
        return ""

