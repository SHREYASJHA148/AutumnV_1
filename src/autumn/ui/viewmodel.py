"""Main-thread presentation; disk I/O and simulated work stay in the worker."""
from __future__ import annotations

import time
from uuid import uuid4

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from autumn.actions.catalog import (
    AppEntry,
    FolderEntry,
    SiteEntry,
    local_path,
    no_reparse,
    validate_app,
)
from autumn.actions.registry import REGISTRY
from autumn.actions.schemas import FolderArgs, OpenFolder, Plan
from autumn.controller.contracts import CaptureState, Event, HistoryEvent, TaskState
from autumn.controller.state import Session
from autumn.controller.worker import Job, Supervisor
from autumn.storage.settings import Hotkeys, Settings


class ViewModel(QObject):
    changed = Signal()
    settingsChanged = Signal()
    shortcutsChanged = Signal()
    acknowledged = Signal(str)

    def __init__(self, supervisor: Supervisor, *, preview_mode: bool = False) -> None:
        super().__init__()
        self.supervisor = supervisor
        self.session = Session()
        self.settings = Settings()
        self.preview_mode = preview_mode
        self.ready = False
        self.settings_pending = False
        self.notice = "Starting the local workspace…"
        self.conversation = [{"role": "Autumn", "text": "Welcome. Type ‘what can you do?’ for available commands. Add or import and review apps in Settings before opening them."}]
        self.history: list[dict] = []
        self.diagnostics: list[dict] = []
        self.shortcut_rows: list[dict] = []
        self.started_requests: dict[str, float] = {}
        self.deferred_records: list[HistoryEvent] = []
        self.pending_inputs: dict[str, str | Plan] = {}
        self.result_cards: list[dict] = []
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    @Property(str, notify=changed)
    def taskStatus(self):
        return self.session.task.value.replace("_", " ").title()

    @Property(str, notify=changed)
    def captureStatus(self):
        return "Voice ready · microphone closed (preview)" if self.session.capture == CaptureState.PTT_READY else "Microphone off"

    @Property(bool, notify=changed)
    def voiceReady(self):
        return self.session.capture == CaptureState.PTT_READY

    @Property(bool, notify=changed)
    def canSend(self):
        return self.ready and not self.session.suspended

    @Property(bool, notify=changed)
    def canConfigure(self):
        return self.canSend and not self.settings_pending

    @Property(str, notify=changed)
    def statusMessage(self):
        return self.notice

    @Property(int, notify=changed)
    def queuedCount(self):
        return len(self.session.pending)

    @Property("QVariantList", notify=changed)
    def messages(self):
        return self.conversation

    @Property("QVariantList", notify=changed)
    def activity(self):
        return self.history

    @Property("QVariantList", notify=changed)
    def health(self):
        return self.diagnostics + self.shortcut_rows

    @Property("QVariantList", notify=changed)
    def resultCards(self):
        return self.result_cards

    @Property("QVariantList", notify=settingsChanged)
    def appCatalog(self):
        return [{**a.model_dump(), "alias_text": ", ".join(a.aliases)} for a in self.settings.apps]

    @Property("QVariantList", notify=settingsChanged)
    def skillSettings(self):
        return [{"id": s.name, "description": s.description, "enabled": s.name in self.settings.enabled_skills} for s in REGISTRY.values() if s.available]

    @Property("QVariantList", notify=settingsChanged)
    def registeredLocations(self):
        return [{"id": f.id, "name": f.name, "detail": f.path, "kind": "folder"} for f in self.settings.folders] + [{"id": s.id, "name": s.name, "detail": s.url, "kind": "site"} for s in self.settings.sites]

    @Property(int, notify=settingsChanged)
    def retentionDays(self):
        return self.settings.history_days

    @Property(str, notify=settingsChanged)
    def stopShortcut(self):
        return self.settings.hotkeys.stop

    @Property(str, notify=settingsChanged)
    def voiceShortcut(self):
        return self.settings.hotkeys.voice_toggle

    @Property(str, notify=settingsChanged)
    def locations(self):
        return "Screenshots: " + self.settings.screenshot_folder + "\nSearch: " + ", ".join(self.settings.search_roots)

    def append(self, role: str, text: str) -> None:
        self.conversation = (self.conversation + [{"role": role, "text": text}])[-100:]

    def schedule(self, kind: str, **kwargs) -> bool:
        if kind in {"save_settings", "import_catalog"} and self.settings_pending:
            self.notice = "Wait for the current settings change to finish."
            self.changed.emit()
            return False
        if not self.supervisor.submit(Job(kind=kind, generation=self.session.generation, **kwargs)):
            self.notice = "Background queue unavailable. Try again shortly; Stop stays available."
            self.changed.emit()
            return False
        if kind in {"save_settings", "import_catalog"}:
            self.settings_pending = True
            self.changed.emit()
        return True

    def persist(self, records: tuple[HistoryEvent, ...]) -> None:
        if not records:
            return
        if not self.supervisor.submit(Job(kind="record", generation=self.session.generation, records=records)):
            # Only redacted metadata; retain a bounded retry batch for a restarted worker.
            self.deferred_records = (self.deferred_records + list(records))[-128:]

    @Slot(str)
    def submit(self, text: str) -> None:
        if not self.canSend:
            return
        text = text.strip()
        if not text:
            return
        if len(text) > 2000:
            self.notice = "Please use at most 2,000 characters."
            self.changed.emit()
            return
        previous = self.session.active
        request = self.session.enqueue()
        if request is None:
            self.notice = "Busy: one request running and five queued. Wait or use Stop."
            self.changed.emit()
            self.acknowledged.emit("input")
            return
        self.append("You", text)
        self.started_requests[str(request.request_id)] = time.monotonic()
        self.pending_inputs[str(request.request_id)] = text
        self.notice = "Checking the command and registered target…"
        if previous is None and not self.dispatch_request(request):
            self.cancel_all("Background worker unavailable.")
        self.changed.emit()
        self.acknowledged.emit("input")

    def cancel_all(self, message: str, code: str = "CANCELLED") -> None:
        active = self.session.active
        uncertain = not self.preview_mode and self.session.task == TaskState.EXECUTING
        cancelled = self.session.stop()
        self.supervisor.cancel(self.session.generation)
        self.pending_inputs.clear()
        records = tuple(self.record(request, "partial" if uncertain and request == active else (
            "cancelled" if code == "CANCELLED" else "failed"), code) for request in cancelled)
        self.persist(records)
        self.notice = message
        if cancelled:
            self.append("Autumn", message)
        self.changed.emit()

    def record(self, request, status: str, code: str) -> HistoryEvent:
        started = self.started_requests.pop(str(request.request_id), time.monotonic())
        return HistoryEvent(request_id=request.request_id, origin=request.origin, status=status,
                            code=code, skill_id="foundation.preview" if self.preview_mode else "controller.request",
                            duration_ms=int((time.monotonic() - started) * 1000))

    @Slot()
    def stop(self) -> None:
        self.cancel_all("Stopped. Queued commands discarded; completed or already accepted effects have not been reversed.")
        self.acknowledged.emit("stop")

    def dispatch_request(self, request) -> bool:
        if self.preview_mode:
            return self.schedule("simulate", request=request)
        content = self.pending_inputs.pop(str(request.request_id), "")
        return self.schedule("execute", request=request, **({"plan": content} if isinstance(content, Plan) else {"text": content}))

    def finish_request(self) -> None:
        if self.session.active is not None:
            identifier = str(self.session.active.request_id)
            self.pending_inputs.pop(identifier, None)
            self.started_requests.pop(identifier, None)
        following = self.session.finish()
        if following is not None and not self.dispatch_request(following):
            self.cancel_all("Background queue unavailable.")

    @Slot(str)
    def showMatchFolder(self, identifier: str) -> None:
        if not self.canSend or not any(card.get("id") == identifier and card.get("kind") == "match" for card in self.result_cards):
            return
        previous = self.session.active
        request = self.session.enqueue(origin="button")
        if request is None:
            return
        self.pending_inputs[str(request.request_id)] = Plan(steps=(OpenFolder(arguments=FolderArgs(candidate_id=identifier)),))
        self.started_requests[str(request.request_id)] = time.monotonic()
        if previous is None:
            self.dispatch_request(request)
        self.changed.emit()

    def update_settings(self, **changes) -> None:
        try:
            updated = Settings.model_validate({**self.settings.model_dump(), **changes})
            self.schedule("save_settings", settings=updated)
        except ValueError:
            self.notice = "The settings change was invalid. Review the selected values."
            self.changed.emit()

    @Slot()
    def importApps(self) -> None:
        if self.canSend and self.schedule("import_catalog"):
            self.notice = "Importing app metadata. Review and enable each app before using it."
            self.changed.emit()

    @Slot(str, str, str, bool)
    def saveApp(self, identifier: str, name: str, aliases: str, enabled: bool) -> None:
        if not self.canConfigure:
            return
        try:
            entry = next(a for a in self.settings.apps if a.id == identifier)
            entry = validate_app(AppEntry.model_validate({**entry.model_dump(), "name": name.strip(),
                "aliases": tuple(s.strip() for s in aliases.split(",") if s.strip()), "enabled": enabled, "reviewed": True}))
            if self.session.active is not None:
                self.stop()
            self.update_settings(apps=[entry.model_dump() if a.id == identifier else a.model_dump() for a in self.settings.apps])
        except (ValueError, OSError, StopIteration):
            self.notice = "That launch target is unavailable or has changed. Remove it and add it again."
            self.changed.emit()

    @Slot(str)
    def removeApp(self, identifier: str) -> None:
        if not self.canConfigure:
            return
        if self.session.active is not None:
            self.stop()
        self.update_settings(apps=[a.model_dump() for a in self.settings.apps if a.id != identifier])

    @Slot()
    def addApp(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(None, "Select an app to register", "", "Apps (*.exe *.lnk)")
        if not filename:
            return
        try:
            path = local_path(filename)
            entry = validate_app(AppEntry(id="a-" + uuid4().hex, name=path.stem[:80], kind="shortcut" if path.suffix.lower() == ".lnk" else "executable", target=str(path)))
            self.update_settings(apps=[*(a.model_dump() for a in self.settings.apps), entry.model_dump()])
        except (ValueError, OSError):
            self.notice = "Choose a local executable or supported shortcut."
            self.changed.emit()

    @Slot(str)
    def addFolder(self, name: str) -> None:
        if not name.strip():
            return
        selected = QFileDialog.getExistingDirectory(None, "Select a registered search folder")
        if not selected:
            return
        try:
            path = no_reparse(local_path(selected))
            entry = FolderEntry(id="f-" + uuid4().hex, name=name.strip(), path=str(path))
            self.update_settings(folders=[*(f.model_dump() for f in self.settings.folders), entry.model_dump()])
        except (ValueError, OSError):
            self.notice = "Choose an accessible local folder without reparse points."
            self.changed.emit()

    @Slot(str, str)
    def addSite(self, name: str, url: str) -> None:
        try:
            entry = SiteEntry(id="s-" + uuid4().hex, name=name.strip(), url=url.strip())
            self.update_settings(sites=[*(s.model_dump() for s in self.settings.sites), entry.model_dump()])
        except ValueError:
            self.notice = "Use a name and a valid HTTP/HTTPS address."
            self.changed.emit()

    @Slot(str, str)
    def removeLocation(self, identifier: str, kind: str) -> None:
        if not self.canConfigure:
            return
        if self.session.active is not None:
            self.stop()
        if kind == "folder":
            self.update_settings(folders=[f.model_dump() for f in self.settings.folders if f.id != identifier])
        elif kind == "site":
            self.update_settings(sites=[s.model_dump() for s in self.settings.sites if s.id != identifier])

    @Slot(str, bool)
    def enableSkill(self, identifier: str, enabled: bool) -> None:
        if not self.canConfigure:
            return
        if not enabled and self.session.active is not None:
            self.stop()
        skills = set(self.settings.enabled_skills)
        skills.add(identifier) if enabled else skills.discard(identifier)
        self.update_settings(enabled_skills=tuple(sorted(skills)))

    @Slot()
    def chooseScreenshotFolder(self) -> None:
        selected = QFileDialog.getExistingDirectory(None, "Select screenshot folder")
        if selected:
            try:
                self.update_settings(screenshot_folder=str(no_reparse(local_path(selected))))
            except (ValueError, OSError):
                self.notice = "Choose an accessible local screenshot folder."
                self.changed.emit()

    @Slot()
    def toggleVoice(self) -> None:
        if self.session.suspended:
            return
        if self.session.capture == CaptureState.PTT_READY:
            self.session.set_capture(CaptureState.DISABLED)
            self.notice = "Microphone off. This phase never opens an audio stream."
        else:
            self.session.set_capture(CaptureState.PTT_READY)
            self.notice = "Voice readiness preview enabled. Live recording arrives in Phase 4."
        self.changed.emit()

    @Slot(int, str, str)
    def saveSettings(self, days: int, stop: str, voice: str) -> None:
        try:
            if stop == voice:
                raise ValueError("Duplicate shortcut")
            settings = Settings.model_validate({**self.settings.model_dump(), "history_days": days,
                "hotkeys": Hotkeys(stop=stop, voice_toggle=voice).model_dump()})
        except ValueError:
            self.notice = "Choose different supported shortcuts and 1–90 history days."
            self.changed.emit()
            return
        self.schedule("save_settings", settings=settings)

    @Slot()
    def clearHistory(self) -> None:
        # Active records must not repopulate a just-cleared history.
        if self.session.active is not None:
            self.stop()
        if self.schedule("clear_history"):
            self.notice = "Clearing Autumn activity records. Exported files are separate."
            self.changed.emit()

    @Slot()
    def refreshDiagnostics(self) -> None:
        self.schedule("diagnostics")

    def suspend(self) -> None:
        self.cancel_all("Paused for lock or sleep. Microphone remains off on return.")
        self.session.suspend()
        self.supervisor.cancel(self.session.generation)
        self.changed.emit()

    def resume(self) -> None:
        self.session.resume()
        self.notice = "Welcome back. Microphone is off; re-enable voice readiness explicitly."
        self.changed.emit()

    def poll(self) -> None:
        for message in self.supervisor.poll():
            kind = message["kind"]
            if kind in {"ready", "settings_saved"}:
                self.settings_pending = False
                self.settings = Settings.model_validate(message["settings"])
                self.ready = True
                self.notice = "Recovered settings safely; microphone off." if message.get("code") == "RECOVERED_DEFAULTS" else "Workspace ready. Typed commands are available; microphone off."
                if message.get("code") == "STORAGE_UNAVAILABLE":
                    self.notice = "Storage unavailable. Using safe settings in memory; activity may not be saved."
                if kind == "ready":
                    self.history = message["history"]
                    self.diagnostics = message["diagnostics"]
                    if self.deferred_records:
                        pending, self.deferred_records = tuple(self.deferred_records), []
                        self.persist(pending)
                self.settingsChanged.emit()
                self.shortcutsChanged.emit()
            elif kind == "history":
                self.history = message["rows"]
            elif kind == "diagnostics":
                self.diagnostics = message["rows"]
            elif kind == "event":
                event = Event.model_validate(message["event"])
                if not self.session.accepts(event):
                    continue
                if event.kind == "TaskStateChanged":
                    self.session.set_task(TaskState(event.state))
                elif event.kind == "StepFinished":
                    request = self.session.active
                    self.persist((self.record(request, "unverified", "SIMULATED"),))
                    self.append("Autumn", "Preview complete. No computer action was performed.")
                    self.notice = "Preview complete."
                    self.finish_request()
            elif kind in {"action_result", "action_finished"}:
                if self.session.active is None or str(self.session.active.request_id) != message["request_id"] or self.session.generation != message["generation"]:
                    continue
                if kind == "action_result":
                    outcome = message["outcome"]
                    self.append("Autumn", outcome["message"])
                    self.notice = outcome["status"].title() + ": " + outcome["message"]
                    if message.get("skill") == "files.search" or outcome.get("matches") or outcome.get("artifacts"):
                        self.result_cards = [*outcome.get("matches", []), *outcome.get("artifacts", [])][-20:]
                if kind == "action_finished" or message.get("finished"):
                    self.finish_request()
            elif kind == "worker_failed":
                self.settings_pending = False
                self.ready = False
                self.cancel_all("Background worker stopped. Interrupted work will not be replayed.", "WORKER_UNAVAILABLE")
                self.notice = "Worker disabled after three failures. Restart Autumn to recover." if message["disabled"] else "Recovering background worker; interrupted work will not be replayed."
            elif kind == "error":
                self.settings_pending = False
                self.notice = "Settings or activity could not be read or saved. Check free space and folder access."
            self.changed.emit()

    def shutdown(self) -> bool:
        self.timer.stop()
        self.session.stop()
        self.supervisor.cancel(self.session.generation)
        return self.supervisor.shutdown()
