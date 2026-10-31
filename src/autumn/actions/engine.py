"""Semantic resolution, independent policy and guarded serial dispatch."""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol
from uuid import uuid4

from autumn.actions.catalog import local_path, no_reparse, safe_url, validate_app, within
from autumn.actions.registry import REGISTRY, capabilities
from autumn.actions.routines import RoutinePlan
from autumn.actions.schemas import Action, Plan
from autumn.controller.contracts import Contract, HistoryEvent, Request
from autumn.policy.matrix import Decision, decide


@dataclass(frozen=True)
class Candidate:
    path: Path
    root: Path
    expires: float


@dataclass(frozen=True)
class Resolved:
    action: Action
    target: object = None
    registered_site: bool = False


class Outcome(Contract):
    status: str
    code: str
    message: str
    verification: str
    artifacts: tuple[dict, ...] = ()
    matches: tuple[dict, ...] = ()


class Adapter(Protocol):
    def perform(self, resolved: Resolved, permit: Decision, checkpoint: Callable[[], bool]) -> Outcome: ...


class Engine:
    def __init__(self, adapter: Adapter, settings, *, clock=time.monotonic) -> None:
        self.adapter, self.settings, self.clock = adapter, settings, clock
        self.candidates: dict[str, Candidate] = {}

    def resolve(self, action: Action) -> Resolved:
        args = action.arguments
        if action.skill == "text.type":
            return Resolved(action, self.adapter.dictation.resolve(args.target_id))
        if action.skill == "routine.run":
            routine = next((r for r in self.settings.routines if r.id == args.routine_id), None)
            if routine is None:
                raise LookupError("Routine not found")
            return Resolved(action, routine)
        if action.skill == "app.open":
            entry = next((a for a in self.settings.apps if a.id == args.app_id and a.enabled and a.reviewed), None)
            if entry is None:
                raise LookupError("Unknown reviewed app")
            return Resolved(action, validate_app(entry))
        if action.skill == "folder.open":
            if bool(args.folder_id) == bool(args.candidate_id):
                raise ValueError("Choose exactly one folder reference")
            if args.candidate_id:
                candidate = self.candidates.get(args.candidate_id)
                if candidate is None or candidate.expires < self.clock():
                    raise LookupError("Search selection expired")
                path = within(candidate.path, candidate.root)
                return Resolved(action, path if path.is_dir() else path.parent)
            folder = next((f for f in self.settings.folders if f.id == args.folder_id), None)
            if folder is None:
                raise LookupError("Unknown folder")
            path = no_reparse(local_path(folder.path))
            if not path.is_dir():
                raise ValueError("Not a directory")
            return Resolved(action, path)
        if action.skill == "website.open":
            if bool(args.site_id) == bool(args.url):
                raise ValueError("Choose exactly one website reference")
            if args.site_id:
                site = next((s for s in self.settings.sites if s.id == args.site_id), None)
                if site is None:
                    raise LookupError("Unknown registered site")
                return Resolved(action, safe_url(site.url), True)
            return Resolved(action, safe_url(args.url))
        if action.skill == "files.search":
            roots = []
            for identifier in args.root_ids:
                folder = next((f for f in self.settings.folders if f.id == identifier and f.search), None)
                if folder is None:
                    raise LookupError("Unknown search root")
                root = no_reparse(local_path(folder.path))
                if not root.is_dir():
                    raise ValueError("Search root unavailable")
                roots.append(root)
            return Resolved(action, tuple(roots))
        if action.skill == "screen.capture":
            path = local_path(self.settings.screenshot_folder)
            # Validate all existing ancestors before creating a screenshot directory.
            parent = path
            while not parent.exists():
                parent = parent.parent
            no_reparse(parent)
            return Resolved(action, path)
        return Resolved(action)

    def execute(self, plan: Plan, request: Request, checkpoint: Callable[[], bool],
                on_step: Callable[[HistoryEvent, Outcome], None], inherited_origin=None,
                on_dispatch: Callable[[float], None] = lambda _: None,
                confirm=lambda *args: False) -> list[Outcome]:
        # Validate again at the process boundary, even for application-created plans.
        plan = (RoutinePlan if isinstance(plan, RoutinePlan) else Plan).model_validate(plan.model_dump(mode="json"))
        if any(a.skill == "routine.run" for a in plan.steps) and (isinstance(plan, RoutinePlan) or len(plan.steps) != 1):
            raise ValueError("Routine must be the only action and cannot nest")
        results = []
        for step_id, action in enumerate(plan.steps, 1):
            started = self.clock()
            deadline = started + REGISTRY[action.skill].timeout

            def valid() -> bool:
                return self.clock() <= deadline and checkpoint()

            if not valid():
                break
            try:
                if action.skill not in self.settings.enabled_skills:
                    outcome = Outcome(status="failed", code="DISABLED", message="That capability is disabled.", verification="policy")
                else:
                    resolved = self.resolve(action)
                    permission = decide(action.skill, request.origin, registered_site=resolved.registered_site,
                                        inherited_origin=inherited_origin)
                    if permission.outcome == "confirm":
                        # Confirmation time is excluded from the action deadline; all other guards remain.
                        approved = confirm(resolved, request, step_id, checkpoint)
                        deadline = self.clock() + REGISTRY[action.skill].timeout
                        if approved and valid():
                            permission = Decision("allow", "Bound single-use confirmation")
                        else:
                            permission = Decision("deny", "Confirmation cancelled, expired, or target changed")
                    if permission.outcome != "allow":
                        outcome = Outcome(status="failed", code="DENIED", message=permission.reason + ". This request was not dispatched.", verification="policy")
                    elif not valid():
                        break
                    elif action.skill == "help.capabilities":
                        outcome = Outcome(status="succeeded", code="OK", message=capabilities(self.settings.enabled_skills), verification="registry")
                    elif action.skill == "routine.run":
                        return self.execute(RoutinePlan(steps=resolved.target.steps), request, checkpoint, on_step,
                            inherited_origin=inherited_origin, on_dispatch=on_dispatch, confirm=confirm)
                    else:
                        on_dispatch(REGISTRY[action.skill].timeout)
                        outcome = self.adapter.perform(resolved, permission, valid)
            except InterruptedError:
                outcome = Outcome(status="cancelled", code="CANCELLED", message="Stopped; completed effects have not been reversed.", verification="cancellation checkpoint")
            except PermissionError:
                outcome = Outcome(status="failed", code="ACCESS_DENIED", message="Windows denied access. No privilege escalation was attempted.", verification="Windows result")
            except LookupError:
                outcome = Outcome(status="failed", code="UNKNOWN_TARGET", message="That registered target is unavailable or the search selection expired.", verification="registry")
            except (ValueError, OSError):
                outcome = Outcome(status="failed", code="INVALID_ARGUMENTS", message="Target validation failed. Review the registered target or address.", verification="semantic checks")
            except Exception:
                outcome = Outcome(status="failed", code="COMPONENT_UNAVAILABLE", message="The Windows component is unavailable. The action was not retried.", verification="adapter error")
            results.append(outcome)
            # No command/argument/path enters history; request/step IDs bind the outcomes.
            record = HistoryEvent(request_id=request.request_id, step_id=step_id, origin=request.origin,
                skill_id=action.skill, status=outcome.status, code=outcome.code,
                duration_ms=int((self.clock() - started) * 1000))
            on_step(record, outcome)
            if outcome.status not in {"succeeded", "unverified"}:
                break
        return results

    def register_matches(self, paths: list[tuple[Path, Path]]) -> tuple[dict, ...]:
        self.candidates.clear()
        rows = []
        for path, root in paths[:20]:
            canonical = within(path, root)
            identifier = uuid4().hex
            self.candidates[identifier] = Candidate(canonical, root, self.clock() + 30)
            rows.append({"id": identifier, "name": canonical.name, "path": str(canonical), "kind": "match"})
        return tuple(rows)
