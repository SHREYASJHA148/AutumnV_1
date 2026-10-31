"""Versioned settings; safe defaults and atomic replacement, including recovery."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field, ValidationError, field_validator, model_validator

from autumn.controller.contracts import Contract

MODEL_DIGEST = "8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7"


class Hotkeys(Contract):
    stop: str = "Ctrl+Alt+Backspace"
    voice_toggle: str = "Ctrl+Alt+Space"

    @model_validator(mode="after")
    def distinct(self):
        if self.stop == self.voice_toggle:
            raise ValueError("Shortcuts must be different")
        return self

    @field_validator("stop", "voice_toggle")
    @classmethod
    def chord(cls, value: str) -> str:
        # Deliberately small, reserved-key-free initial catalog.
        allowed = {"Ctrl+Alt+Backspace", "Ctrl+Alt+Space", "Ctrl+Alt+F9", "Ctrl+Alt+F10"}
        if value not in allowed:
            raise ValueError("Choose a supported shortcut")
        return value


class Settings(Contract):
    schema_version: Literal[1] = 1
    microphone_enabled_at_start: Literal[False] = False
    wake_enabled: Literal[False] = False
    conversation_persistence: Literal[False] = False
    microphone: str = "System default — built-in microphone preferred"
    speaker: str = "System default"
    voice: Literal["en_US-lessac-medium"] = "en_US-lessac-medium"
    language: Literal["en"] = "en"
    hotkeys: Hotkeys = Field(default_factory=Hotkeys)
    history_days: int = Field(default=7, ge=1, le=90)
    model_tag: Literal["qwen3:1.7b"] = "qwen3:1.7b"
    model_digest: Literal[MODEL_DIGEST] = MODEL_DIGEST
    enabled_skills: tuple[str, ...] = ()
    screenshot_folder: str = str(Path.home() / "Pictures" / "Autumn")
    search_roots: tuple[str, ...] = (str(Path.home() / "Documents"), str(Path.home() / "Downloads"))


def app_directory() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "Autumn"


def atomic_save(path: Path, settings: Settings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, encoding="utf-8", delete=False) as f:
            temporary = f.name
            f.write(settings.model_dump_json(indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def load_settings(path: Path) -> tuple[Settings, str]:
    if not path.exists():
        settings = Settings()
        atomic_save(path, settings)
        return settings, "DEFAULTS_CREATED"
    try:
        if path.stat().st_size > 64_000:
            raise ValueError("Settings too large")
        return Settings.model_validate_json(path.read_text(encoding="utf-8")), "LOADED"
    except (ValidationError, ValueError, UnicodeError, json.JSONDecodeError):
        # Preserve the original and refuse unsafe overwrite if preservation fails.
        backup = path.with_name(f"settings.recovered-{uuid4().hex}.json")
        os.replace(path, backup)
        settings = Settings()
        atomic_save(path, settings)
        return settings, "RECOVERED_DEFAULTS"
