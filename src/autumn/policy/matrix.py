"""A routine can only inherit authority; it cannot introduce its own origin."""
from dataclasses import dataclass
from typing import Literal

from autumn.actions.registry import REGISTRY
from autumn.actions.schemas import Origin


@dataclass(frozen=True)
class Decision:
    outcome: Literal["allow", "confirm", "deny"]
    reason: str


def decide(skill: str, origin: Origin, *, registered_site: bool = False,
           inherited_origin: Origin | None = None) -> Decision:
    if origin == "routine":
        if inherited_origin is None or inherited_origin == "routine":
            return Decision("deny", "Routine origin missing")
        origin = inherited_origin
    if skill not in REGISTRY or not REGISTRY[skill].available:
        return Decision("deny", "Capability unavailable")
    if origin not in {"typed", "button", "ptt_voice", "wake_voice"}:
        return Decision("deny", "Unknown origin")
    if skill == "text.type":
        return Decision("deny", "Wake requests cannot dictate") if origin == "wake_voice" else Decision("confirm", "Exact text and target require confirmation")
    if skill == "website.open" and not registered_site:
        if origin == "wake_voice":
            return Decision("deny", "Wake requests require a registered website")
        if origin == "ptt_voice":
            return Decision("confirm", "Explicit URL requires confirmation")
    return Decision("allow", "Origin permits this registered capability")
