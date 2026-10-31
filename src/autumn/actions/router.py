"""Bounded deterministic grammar. Unmatched words and negations never dispatch."""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from autumn.actions.schemas import (
    AppArgs,
    Capabilities,
    CaptureScreen,
    FolderArgs,
    MediaArgs,
    MediaControl,
    MuteArgs,
    OpenApp,
    OpenFolder,
    OpenWebsite,
    Plan,
    SearchArgs,
    SearchFiles,
    SetMute,
    SetVolume,
    VolumeArgs,
    WebsiteArgs,
)


@dataclass(frozen=True)
class Routing:
    plan: Plan | None = None
    message: str = "I don't recognize that command. Ask ‘what can you do?’ for supported commands."
    choices: tuple[str, ...] = ()
    allow_model: bool = False


def normalize(text: str) -> str:
    return " ".join(text.casefold().strip().rstrip(".?!").split())


def route(text: str, settings) -> Routing:
    value = normalize(text)
    if not value or len(value) > 2000 or re.search(r"\b(don't|do not|not|never|cancel|instead|then|and|but|except|without)\b|[;|`<>\r\n]", value):
        return Routing(message="Please give one supported command, without extra instructions.")
    action = None
    # Normalize only bounded positive launch phrases, then resolve the entire remaining alias.
    if launch := re.fullmatch(r"(?:(?:please|could you|can you) )?(?:bring up|launch|take me to|show(?: me)?) (?:(?:the|my) )?(.+?)(?: (?:folder|directory|website|site|app|application))?",value):
        value = "open " + launch[1]
    if value in {"help", "what can you do", "show capabilities", "capabilities"}:
        action = Capabilities()
    elif value in {"take a screenshot", "take screenshot", "screenshot", "capture screen"}:
        action = CaptureScreen()
    elif value == "screenshot all monitors":
        action = CaptureScreen(arguments={"monitor": "all"})
    elif match := re.fullmatch(r"(?:set )?volume (?:to )?(\d{1,3})(?: percent|%)?", value):
        if int(match[1]) > 100:
            return Routing(message="Volume must be between 0 and 100 percent.")
        action = SetVolume(arguments=VolumeArgs(percent=int(match[1])))
    elif value in {"mute", "mute speakers", "unmute", "unmute speakers"}:
        action = SetMute(arguments=MuteArgs(muted=value.startswith("mute")))
    elif value in {"play pause", "play/pause", "pause music", "play music", "next track", "previous track", "skip this track", "skip this song"}:
        # Only a toggle is exposed; explicit play/pause ambiguity must not pretend to set a state.
        if value in {"pause music", "play music"}:
            return Routing(message="Use ‘play pause’ to toggle the current media session.")
        action = MediaControl(arguments=MediaArgs(command={"next track": "next", "skip this track":"next", "skip this song":"next", "previous track": "previous"}.get(value, "play_pause")))
    elif match := re.fullmatch(r"search (.+?) for (spreadsheets|pdfs|photos|documents|text files)(?: named| called)? (.+)",value):
        roots = [f for f in settings.folders if f.search and normalize(f.name)==match[1]]
        if not roots:
            return Routing(message="Choose an existing search root in Settings.")
        hint={"spreadsheets":"spreadsheet","pdfs":"pdf","photos":"photo","documents":"document","text files":"text"}[match[2]]
        try:
            action=SearchFiles(arguments=SearchArgs(query=match[3],type_hint=hint,root_ids=tuple(f.id for f in roots)))
        except ValueError:
            return Routing(message="Use a filename fragment without paths or wildcards.")
    elif match := re.fullmatch(r"(?:find|search for) (.+?)(?: in (.+))?", value):
        query, root_name = match[1], match[2]
        roots = [f for f in settings.folders if f.search and (root_name is None or normalize(f.name) == root_name)]
        if not roots:
            return Routing(message="Choose an existing search root in Settings.")
        type_hint = "any"
        for word in ("spreadsheet", "pdf", "photo", "document", "text"):
            if query.startswith(word + " "):
                type_hint, query = word, query[len(word) + 1:]
                break
        try:
            action = SearchFiles(arguments=SearchArgs(query=query, type_hint=type_hint, root_ids=tuple(f.id for f in roots)))
        except ValueError:
            return Routing(message="Search needs a filename fragment, without paths or wildcards.")
    elif match := re.fullmatch(r"open (.+)", value):
        name = match[1]
        if name.startswith(("http:", "https:")):
            # Preserve the original URL's case-sensitive path/query.
            raw = text.strip()[5:].strip()
            action = OpenWebsite(arguments=WebsiteArgs(url=raw))
        else:
            candidates = []
            aliases = []
            for app in settings.apps:
                if app.enabled and app.reviewed:
                    for alias in (app.name, *app.aliases):
                        aliases.append((normalize(alias), "app", app.id, app.name))
            aliases += [(normalize(f.name), "folder", f.id, f.name) for f in settings.folders]
            aliases += [(normalize(s.name), "site", s.id, s.name) for s in settings.sites]
            candidates = list({(kind, identifier, label) for alias, kind, identifier, label in aliases if alias == name})
            if len(candidates) != 1:
                # Fuzzy suggestions never execute, even above 0.90; ask for the exact reviewed name.
                suggestions = sorted({label for alias, _, _, label in aliases if SequenceMatcher(None, name, alias).ratio() >= 0.80})[:5]
                return Routing(message="Use an exact, unique registered name. Review apps and aliases in Settings.", choices=tuple(suggestions))
            kind, identifier, _ = candidates[0]
            action = {"app": lambda: OpenApp(arguments=AppArgs(app_id=identifier)),
                      "folder": lambda: OpenFolder(arguments=FolderArgs(folder_id=identifier)),
                      "site": lambda: OpenWebsite(arguments=WebsiteArgs(site_id=identifier))}[kind]()
    if action is None:
        return Routing(allow_model=True)
    if action.skill not in settings.enabled_skills:
        return Routing(message="That capability is disabled in Settings.")
    return Routing(plan=Plan(steps=(action,)), message="")
