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


@dataclass(slots=True)
class AppState:
    """Holds runtime application state."""

    current_os: str | None = None


APP_STATE = AppState()


def os_key() -> str:
    """Return short OS key for commands.json templates."""
    mapping = {"Windows": "win", "Linux": "astro", "macOS": "macos"}
    return mapping.get(APP_STATE.current_os or "", "")
