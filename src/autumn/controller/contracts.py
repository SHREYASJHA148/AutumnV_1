"""Strict internal contracts. None of these are accepted from model output."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CaptureState(StrEnum):
    DISABLED = "DISABLED"
    PTT_READY = "PTT_READY"
    ARMED_WAKE = "ARMED_WAKE"
    RECORDING = "RECORDING"
    SUSPENDED_PLAYBACK = "SUSPENDED_PLAYBACK"
    DEVICE_ERROR = "DEVICE_ERROR"


class TaskState(StrEnum):
    IDLE = "IDLE"
    TRANSCRIBING = "TRANSCRIBING"
    ROUTING = "ROUTING"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    CANCELLING = "CANCELLING"
    ERROR = "ERROR"


class Request(Contract):
    request_id: UUID = Field(default_factory=uuid4)
    origin: Literal["typed", "button", "ptt_voice", "wake_voice", "routine"] = "typed"
    generation: int = Field(ge=0)
    # Text stays in the UI's bounded, memory-only conversation, never in this queue.


class Event(Contract):
    kind: Literal[
        "CaptureStateChanged", "TaskStateChanged", "TranscriptReady", "PlanReady",
        "ConfirmationRequested", "StepFinished", "SpeechStarted", "SpeechFinished",
        "ComponentUnavailable",
    ]
    request_id: UUID | None = None
    generation: int = Field(ge=0)
    state: CaptureState | TaskState | None = None
    code: Literal["SIMULATED", "CANCELLED", "WORKER_UNAVAILABLE"] | None = None


class HistoryEvent(Contract):
    request_id: UUID
    origin: Literal["typed", "button", "ptt_voice", "wake_voice", "routine"]
    status: Literal["succeeded", "failed", "unverified", "cancelled", "partial"]
    code: Literal["SIMULATED", "CANCELLED", "WORKER_UNAVAILABLE", "OK", "HANDOFF", "UNKNOWN_TARGET",
                  "INVALID_ARGUMENTS", "DENIED", "DISABLED", "ACCESS_DENIED", "NO_SESSION",
                  "UNSUPPORTED", "TIMEOUT", "PARTIAL", "COMPONENT_UNAVAILABLE", "CLARIFICATION"]
    duration_ms: int = Field(ge=0)
    skill_id: Literal["foundation.preview", "controller.request", "app.open", "folder.open", "website.open",
                      "audio.set_volume", "audio.set_mute", "media.control", "screen.capture", "files.search",
                      "help.capabilities", "text.type", "routine.run"] = "foundation.preview"
    step_id: int = Field(default=0, ge=0, le=3)
