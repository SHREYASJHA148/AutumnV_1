"""Compact request-local enums narrow the frozen action arguments, never widen them."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from autumn.actions.catalog import safe_url
from autumn.actions.registry import REGISTRY
from autumn.actions.schemas import ACTION, Plan
from autumn.brain.contracts import REPLY, Answer, BrainError, Clarification


def obj(properties):
    return {"type":"object", "properties":properties, "required":list(properties), "additionalProperties":False}


def enum(values):
    return {"type":"string", "enum":list(values)}


@dataclass
class LiveSchema:
    schema: dict
    catalog: dict
    ids: dict[str, set[str]]
    choices: set[str]

    def parse(self, content: str):
        if len(content.encode("utf-8")) > 8192:
            raise BrainError("RESPONSE_LIMIT")
        try:
            raw = json.loads(content)
            if not isinstance(raw, dict) or raw.get("kind") not in {"action_plan", "clarification", "unsupported", "answer"}:
                raise ValueError()
            reply = REPLY.validate_python(raw)
            if isinstance(reply, Plan):
                if any(a.skill == "routine.run" for a in reply.steps) and len(reply.steps) != 1:
                    raise ValueError()
                for action in reply.steps:
                    if action.skill not in self.ids["skills"]:
                        raise ValueError()
                    args = action.arguments
                    if action.skill == "routine.run" and args.routine_id not in self.ids["routines"]:
                        raise ValueError()
                    if action.skill == "app.open" and args.app_id not in self.ids["apps"]:
                        raise ValueError()
                    if action.skill == "folder.open":
                        if bool(args.folder_id) == bool(args.candidate_id):
                            raise ValueError()
                        if args.folder_id and args.folder_id not in self.ids["folders"]:
                            raise ValueError()
                        if args.candidate_id and args.candidate_id not in self.ids["candidates"]:
                            raise ValueError()
                    if action.skill == "website.open":
                        if bool(args.site_id) == bool(args.url):
                            raise ValueError()
                        if args.site_id and args.site_id not in self.ids["sites"]:
                            raise ValueError()
                        if args.url:
                            safe_url(args.url)
                    if action.skill == "files.search" and (not set(args.root_ids) <= self.ids["roots"] or len(set(args.root_ids)) != len(args.root_ids)):
                        raise ValueError()
            if isinstance(reply, Clarification) and not set(reply.choices) <= self.choices:
                raise ValueError()
            if isinstance(reply,Answer) and "help.capabilities" not in self.ids["skills"]:
                raise ValueError()
            return reply
        except (ValueError, TypeError):
            raise BrainError("INVALID_PLAN") from None


def build_schema(settings, text: str, candidate_ids=()) -> LiveSchema:
    words = set(re.findall(r"\w+", text.casefold()))
    apps = [a for a in settings.apps if a.reviewed and a.enabled]
    apps.sort(key=lambda a: (-len(words & set(re.findall(r"\w+", " ".join((a.name,*a.aliases)).casefold()))), a.id))
    catalog = {"apps":[], "folders":[], "sites":[], "routines":[]}
    for category, entries in (("apps",apps[:16]), ("folders",settings.folders), ("sites",settings.sites[:8])):
        budget = {"apps":600,"folders":350,"sites":250}[category]
        for entry in entries:
            row = {"id":entry.id, "name":entry.name}
            if category == "apps" and entry.aliases:
                row["aliases"] = list(entry.aliases[:2])
            cost = len(json.dumps(row,ensure_ascii=False).encode())
            if cost <= budget:
                catalog[category].append(row)
                budget -= cost
    for routine in settings.routines[:8]:
        if sum(len(json.dumps(row)) for row in catalog["routines"]) + len(routine.name) < 250:
            catalog["routines"].append({"id":routine.id,"name":routine.name})
    ids = {key:{row["id"] for row in catalog[key]} for key in catalog}
    ids["roots"] = {f.id for f in settings.folders if f.search and f.id in ids["folders"]}
    ids["candidates"] = set(candidate_ids[:20])
    choices = {row["name"] for entries in catalog.values() for row in entries}
    variants = []
    # Pull scalar bounds from the frozen models; registry IDs become per-request enums.
    action_variants = ACTION.json_schema()["$defs"]
    argument_names = {"app.open":"AppArgs", "folder.open":"FolderArgs", "website.open":"WebsiteArgs",
        "audio.set_volume":"VolumeArgs", "audio.set_mute":"MuteArgs", "media.control":"MediaArgs",
        "screen.capture":"CaptureArgs", "files.search":"SearchArgs", "help.capabilities":"Empty", "routine.run":"RoutineArgs"}
    skills = set()
    for skill in settings.enabled_skills:
        if skill not in argument_names or not REGISTRY[skill].available:
            continue
        arguments = json.loads(json.dumps(action_variants[argument_names[skill]]))
        if skill == "routine.run":
            if not ids["routines"]:
                continue
            arguments = obj({"routine_id":enum(sorted(ids["routines"]))})
        elif skill == "app.open":
            if not ids["apps"]:
                continue
            arguments = obj({"app_id":enum(sorted(ids["apps"]))})
        elif skill == "folder.open":
            refs = []
            if ids["folders"]:
                refs.append(obj({"folder_id":enum(sorted(ids["folders"]))}))
            if ids["candidates"]:
                refs.append(obj({"candidate_id":enum(sorted(ids["candidates"]))}))
            if not refs:
                continue
            arguments = {"oneOf":refs} if len(refs)>1 else refs[0]
        elif skill == "website.open":
            refs = [obj({"url":{"type":"string","maxLength":2048,"pattern":"^https?://"}})]
            if ids["sites"]:
                refs.insert(0,obj({"site_id":enum(sorted(ids["sites"]))}))
            arguments = {"oneOf":refs}
        elif skill == "files.search":
            if not ids["roots"]:
                continue
            arguments["properties"]["root_ids"]["items"] = enum(sorted(ids["roots"]))
            arguments["properties"]["root_ids"]["uniqueItems"] = True
        variants.append(obj({"skill":{"const":skill}, "arguments":arguments}))
        skills.add(skill)
    ids["skills"] = skills
    replies = []
    if variants:
        replies.append(obj({"kind":{"const":"action_plan"}, "steps":{"type":"array","minItems":1,"maxItems":3,"items":{"oneOf":variants}}}))
    message = {"type":"string","minLength":1,"maxLength":180}
    choice_schema = enum(sorted(choices)) if choices else {"type":"string","maxLength":80}
    replies.extend([
        obj({"kind":{"const":"clarification"}, "message":message,
             "choices":{"type":"array","maxItems":min(5,len(choices)),"items":choice_schema}}),
        obj({"kind":{"const":"unsupported"}, "message":message}),
    ])
    if "help.capabilities" in skills:
        replies.append(obj({"kind":{"const":"answer"}, "text":{"type":"string","minLength":1,"maxLength":300}}))
    return LiveSchema({"oneOf":replies},catalog,ids,choices)
