"""Capability declarations and the single inventory used for help and execution."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    timeout: float
    verification: str
    side_effect: str
    retry: str = "never automatically replay"
    cancellation: str = "before dispatch and between bounded checkpoints"
    preconditions: str = "enabled, resolved, session unlocked, policy allows origin"
    permission: str = "local desktop"
    version: int = 1
    available: bool = True


REGISTRY = {s.name: s for s in (
    Skill("app.open", "Open a reviewed app", 10, "process/new window or unverified handoff", "launch app"),
    Skill("folder.open", "Open a registered folder or show a search match's folder", 5, "shell handoff; window unverified", "open Explorer"),
    Skill("website.open", "Open a registered website or an explicit HTTP/HTTPS address", 5, "browser handoff; page unverified", "open browser"),
    Skill("audio.set_volume", "Set volume to 0–100 percent", 5, "Core Audio read-back", "change session volume"),
    Skill("audio.set_mute", "Mute or unmute speakers", 5, "Core Audio read-back", "change session mute"),
    Skill("media.control", "Play/pause, next or previous media", 5, "session acceptance and playback state when available", "control current media"),
    Skill("screen.capture", "Save a screenshot of the primary or all monitors", 15, "nonzero PNG dimensions and file", "save an image"),
    Skill("files.search", "Find filenames inside configured roots", 12, "root and reparse checks; limits disclosed", "read filename metadata"),
    Skill("help.capabilities", "Show this capabilities list", 5, "registry generated", "none"),
    Skill("text.type", "Confirmed dictation (Phase 5)", 10, "foreground target between chunks", "type text", available=False),
    Skill("routine.run", "Named routines (Phase 5)", 15, "per-step outcomes", "per-step effects", available=False),
)}
DEFAULT_ENABLED = tuple(s.name for s in REGISTRY.values() if s.available)


def capabilities(enabled: tuple[str, ...]) -> str:
    return "I can: " + "; ".join(s.description for s in REGISTRY.values() if s.available and s.name in enabled) + "."
