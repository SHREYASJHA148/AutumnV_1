"""Acceptance needs measured trials, never an unchecked user toggle or model claim."""

import json
import os
import tempfile

from pydantic import Field, model_validator

from autumn.controller.contracts import Contract


class Calibration(Contract):
    profile: str = Field(pattern="^[0-9a-f]{64}$")
    trials: int = Field(default=0, ge=0, le=50)
    hits: int = Field(default=0, ge=0, le=50)
    negative_seconds: float = Field(default=0, ge=0, le=86400)
    false_triggers: int = Field(default=0, ge=0)
    cpu_window_seconds: float = Field(default=0, ge=0)
    cpu_percent: float = Field(default=100, ge=0, le=100)
    on_mains: bool = False

    @model_validator(mode="after")
    def coherent(self):
        if self.hits > self.trials:
            raise ValueError("More detections than trials")
        return self

    @property
    def accepted(self):
        return (
            self.trials == 50
            and self.hits >= 45
            and self.negative_seconds >= 7200
            and self.false_triggers / self.negative_seconds * 3600 <= 1
            and self.cpu_window_seconds >= 300
            and self.cpu_percent < 5
            and self.on_mains
        )


def load(root):
    try:
        return Calibration.model_validate_json(
            (root / "config/wake-calibration.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return None


def save(root, record):
    path = root / "config/wake-calibration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, encoding="utf-8", delete=False
        ) as stream:
            temporary = stream.name
            json.dump(record.model_dump(), stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
