"""Main-thread presentation; disk I/O and simulated work stay in the worker."""
from __future__ import annotations

import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from autumn.controller.contracts import CaptureState, Event, HistoryEvent, TaskState
from autumn.controller.state import Session
from autumn.controller.worker import Job, Supervisor
from autumn.storage.settings import Hotkeys, Settings


class ViewModel(QObject):
    changed = Signal()
    settingsChanged = Signal()
    shortcutsChanged = Signal()
    acknowledged = Signal(str)

    def __init__(self, supervisor: Supervisor) -> None:
        super().__init__()
        self.supervisor = supervisor
        self.session = Session()
        self.settings = Settings()
        self.ready = False
        self.notice = "Starting the local workspace…"
        self.conversation = [{"role": "Autumn", "text": "Welcome. Try a typed request to preview the flow. Computer actions and voice arrive in later phases."}]
        self.history: list[dict] = []
        self.diagnostics: list[dict] = []
        self.shortcut_rows: list[dict] = []
        self.started_requests: dict[str, float] = {}
        self.deferred_records: list[HistoryEvent] = []
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
        if not self.supervisor.submit(Job(kind=kind, generation=self.session.generation, **kwargs)):
            self.notice = "Background queue unavailable. Try again shortly; Stop stays available."
            self.changed.emit()
            return False
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
        self.notice = "Preview running. No computer action will be performed."
        if previous is None and not self.schedule("simulate", request=request):
            self.cancel_all("Background worker unavailable.")
        self.changed.emit()
        self.acknowledged.emit("input")

    def cancel_all(self, message: str, code: str = "CANCELLED") -> None:
        cancelled = self.session.stop()
        self.supervisor.cancel(self.session.generation)
        records = tuple(self.record(request, "cancelled" if code == "CANCELLED" else "failed", code) for request in cancelled)
        self.persist(records)
        self.notice = message
        if cancelled:
            self.append("Autumn", message)
        self.changed.emit()

    def record(self, request, status: str, code: str) -> HistoryEvent:
        started = self.started_requests.pop(str(request.request_id), time.monotonic())
        return HistoryEvent(request_id=request.request_id, origin=request.origin, status=status,
                            code=code, duration_ms=int((time.monotonic() - started) * 1000))

    @Slot()
    def stop(self) -> None:
        self.cancel_all("Stopped. Queued previews discarded; no computer actions were performed.")
        self.acknowledged.emit("stop")

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
                self.settings = Settings.model_validate(message["settings"])
                self.ready = True
                self.notice = "Recovered settings safely; microphone off." if message.get("code") == "RECOVERED_DEFAULTS" else "Workspace ready. Phase 1 previews only."
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
                    following = self.session.finish()
                    if following is not None and not self.schedule("simulate", request=following):
                        self.cancel_all("Background queue unavailable.")
            elif kind == "worker_failed":
                self.ready = False
                self.cancel_all("Background worker stopped. Interrupted work will not be replayed.", "WORKER_UNAVAILABLE")
                self.notice = "Worker disabled after three failures. Restart Autumn to recover." if message["disabled"] else "Recovering background worker; interrupted work will not be replayed."
            elif kind == "error":
                self.notice = "Settings or activity could not be read or saved. Check free space and folder access."
            self.changed.emit()

    def shutdown(self) -> bool:
        self.timer.stop()
        self.session.stop()
        self.supervisor.cancel(self.session.generation)
        return self.supervisor.shutdown()
