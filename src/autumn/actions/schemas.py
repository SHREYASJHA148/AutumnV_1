"""Version 1 action vocabulary. Paths and authority never appear in planner arguments."""
from __future__ import annotations

import re
import unicodedata
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, TypeAdapter, field_validator

from autumn.controller.contracts import Contract

Identifier = Annotated[StrictStr, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")]
Origin = Literal["typed", "button", "ptt_voice", "wake_voice", "routine"]
SkillId = Literal["app.open", "folder.open", "website.open", "audio.set_volume", "audio.set_mute",
                  "media.control", "screen.capture", "files.search", "help.capabilities", "text.type", "routine.run"]


class Empty(Contract):
    pass


class AppArgs(Contract):
    app_id: Identifier


class FolderArgs(Contract):
    folder_id: Identifier | None = None
    candidate_id: Identifier | None = None


class WebsiteArgs(Contract):
    site_id: Identifier | None = None
    url: Annotated[StrictStr, Field(min_length=1, max_length=2048)] | None = None


class VolumeArgs(Contract):
    percent: Annotated[StrictInt, Field(ge=0, le=100)]


class MuteArgs(Contract):
    muted: StrictBool


class MediaArgs(Contract):
    command: Literal["play_pause", "next", "previous"]


class CaptureArgs(Contract):
    monitor: Literal["primary", "all"] = "primary"


class SearchArgs(Contract):
    query: Annotated[StrictStr, Field(min_length=1, max_length=80)]
    type_hint: Literal["any", "pdf", "spreadsheet", "photo", "document", "text"] = "any"
    root_ids: Annotated[tuple[Identifier, ...], Field(min_length=1, max_length=8)]

    @field_validator("query")
    @classmethod
    def safe_query(cls, value: str) -> str:
        if re.search(r"[\x00-\x1f\x7f\\/:*?<>|]", value) or not value.strip():
            raise ValueError("Use a filename fragment, not a path or pattern")
        return value.strip()


class TextArgs(Contract):
    text: Annotated[StrictStr, Field(min_length=1, max_length=1000)]
    target_id: Identifier

    @field_validator("text")
    @classmethod
    def no_controls(cls, value: str) -> str:
        if any(unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for c in value):
            raise ValueError("Control characters not supported")
        return value


class RoutineArgs(Contract):
    routine_id: Identifier


class OpenApp(Contract):
    skill: Literal["app.open"] = "app.open"
    arguments: AppArgs


class OpenFolder(Contract):
    skill: Literal["folder.open"] = "folder.open"
    arguments: FolderArgs


class OpenWebsite(Contract):
    skill: Literal["website.open"] = "website.open"
    arguments: WebsiteArgs


class SetVolume(Contract):
    skill: Literal["audio.set_volume"] = "audio.set_volume"
    arguments: VolumeArgs


class SetMute(Contract):
    skill: Literal["audio.set_mute"] = "audio.set_mute"
    arguments: MuteArgs


class MediaControl(Contract):
    skill: Literal["media.control"] = "media.control"
    arguments: MediaArgs


class CaptureScreen(Contract):
    skill: Literal["screen.capture"] = "screen.capture"
    arguments: CaptureArgs = Field(default_factory=CaptureArgs)


class SearchFiles(Contract):
    skill: Literal["files.search"] = "files.search"
    arguments: SearchArgs


class Capabilities(Contract):
    skill: Literal["help.capabilities"] = "help.capabilities"
    arguments: Empty = Field(default_factory=Empty)


class TypeText(Contract):
    skill: Literal["text.type"] = "text.type"
    arguments: TextArgs


class RunRoutine(Contract):
    skill: Literal["routine.run"] = "routine.run"
    arguments: RoutineArgs


Action = Annotated[OpenApp | OpenFolder | OpenWebsite | SetVolume | SetMute | MediaControl |
                   CaptureScreen | SearchFiles | Capabilities | TypeText | RunRoutine,
                   Field(discriminator="skill")]
ACTION = TypeAdapter(Action)


class Plan(Contract):
    kind: Literal["action_plan"] = "action_plan"
    steps: Annotated[tuple[Action, ...], Field(min_length=1, max_length=3)]


def parse_plan(text: str) -> Plan:
    if len(text.encode("utf-8")) > 8192:
        raise ValueError("Oversized plan")
    return Plan.model_validate_json(text)
