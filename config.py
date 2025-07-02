"""Application configuration and state management."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).with_name('.env')
    if env_path.exists():
        with env_path.open('r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.lstrip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ.setdefault(key, value)



_load_dotenv()

DEEPSEEK_API_KEY: str | None = os.getenv('DEEPSEEK_API_KEY')
THEME: str = os.getenv("APP_THEME", "dark")


@dataclass(slots=True)
class AppState:
    """Holds runtime application state."""

    current_os: str | None = None


APP_STATE = AppState()


def os_key() -> str:
    """Return short OS key for commands.json templates."""
    mapping = {"Windows": "win", "Linux": "astro", "macOS": "macos"}
    return mapping.get(APP_STATE.current_os or "", "")


def apply_theme(app, theme: str | None = None) -> None:
    """Load and apply QSS theme to the application."""
    if theme is None:
        theme = THEME
    mapping = {"dark": "styles.qss", "light": "light.qss"}
    fname = mapping.get(theme, f"{theme}.qss")
    path = Path(__file__).resolve().parent / "resources" / fname
    if path.exists():
        app.setStyleSheet(path.read_text(encoding="utf-8"))
    else:
        app.setStyleSheet("")
