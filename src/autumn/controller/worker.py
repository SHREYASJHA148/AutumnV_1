"""Supervised process boundary. Test faults cannot be enabled by UI input."""
from __future__ import annotations

import os
import queue
import sqlite3
import time
from collections import deque
from multiprocessing import get_context
from pathlib import Path
from typing import Literal

from pydantic import Field

from autumn.actions.engine import Engine, Outcome
from autumn.actions.registry import REGISTRY, capabilities
from autumn.actions.router import route
from autumn.actions.schemas import Plan
from autumn.brain.contracts import Answer, BrainError, Clarification
from autumn.brain.planner import Planner, recovery_message
from autumn.controller.contracts import Contract, Event, HistoryEvent, Request, TaskState
from autumn.diagnostics.health import snapshot
from autumn.policy.confirmation import Confirmations
from autumn.storage.history import HistoryStore
from autumn.storage.settings import Settings, atomic_save, load_settings
from autumn.winworker.capture import initialize_dpi
from autumn.winworker.windows import WindowsAdapter, import_apps


class Job(Contract):
    kind: Literal["bootstrap", "simulate", "execute", "activate_model", "import_catalog", "save_settings", "history", "clear_history", "record", "diagnostics", "hang", "crash", "dictation_targets", "confirm"]
    generation: int = Field(ge=0)
    request: Request | None = None
    settings: Settings | None = None
    records: tuple[HistoryEvent, ...] = ()
    text: str | None = Field(default=None, max_length=2000)
    plan: Plan | None = None
    confirmation_id: str | None = Field(default=None, max_length=64)
    approved: bool = False


def worker_main(commands, replies, generation, stopping, root: str, allow_faults: bool, *, voice_generation=None) -> None:
    initialize_dpi()
    parent = os.getppid()
    history: HistoryStore | None = None
    settings = Settings()
    adapter = WindowsAdapter(data_dir=Path(root))
    engine = Engine(adapter, settings)
    brain = Planner()
    adapter.engine = engine
    last_beat = 0.0
    last_voice_generation = voice_generation.value if voice_generation is not None else 0
    deferred = deque()
    approvals = Confirmations()

    def send(kind: str, **data) -> None:
        # Bounded IPC; a non-reading parent eventually causes a supervised restart.
        replies.put({"kind": kind, **data}, timeout=0.25)

    def alive() -> bool:
        nonlocal last_beat
        if stopping.is_set() or os.getppid() != parent:
            return False
        if time.monotonic() - last_beat > 0.25:
            send("heartbeat")
            last_beat = time.monotonic()
        return True

    try:
        while alive():
            try:
                job = deferred.popleft() if deferred else Job.model_validate(commands.get(timeout=0.05))
            except queue.Empty:
                continue
            if voice_generation is not None and voice_generation.value!=last_voice_generation:
                if brain.context is not None and brain.context.origin in {'ptt_voice','wake_voice'}:
                    brain.clear_context()
                last_voice_generation=voice_generation.value
            try:
                if job.kind == "bootstrap":
                    code = "LOADED"
                    try:
                        settings, code = load_settings(Path(root) / "config/settings.json")
                    except OSError:
                        settings, code = Settings(), "STORAGE_UNAVAILABLE"
                    try:
                        history = HistoryStore(Path(root) / "data/jarvis.db")
                        history.prune(settings.history_days)
                    except (OSError, ValueError, sqlite3.Error):
                        history, code = None, "STORAGE_UNAVAILABLE"
                    engine.settings = settings
                    send("ready", settings=settings.model_dump(mode="json"), code=code,
                         history=history.list_recent() if history is not None else [], diagnostics=snapshot())
                elif job.kind == "execute" and job.request is not None:
                    req = job.request
                    if req.generation != job.generation or generation.value != req.generation:
                        continue
                    def checkpoint():
                        return (alive() and generation.value == req.generation and
                            (req.origin not in {'ptt_voice','wake_voice'} or voice_generation is None or voice_generation.value==req.voice_generation))
                    if not checkpoint():
                        continue

                    # IPC carries input in memory only. Never add it to history or diagnostics.
                    routing = route(job.text or "", settings) if job.plan is None else None
                    plan = job.plan or (routing.plan if routing else None)
                    model_reply = None
                    model_error = None
                    if plan is None and routing and routing.allow_model and settings.model_enabled:
                        send("busy", timeout=15.3)
                        try:
                            candidate_ids = tuple(k for k,v in engine.candidates.items() if v.expires >= time.monotonic())
                            model_reply = brain.plan(job.text or "",settings,req,checkpoint,candidate_ids)
                            if isinstance(model_reply,Plan):
                                plan = model_reply
                        except BrainError as error:
                            model_error = error.code
                        send("model_status",message=brain.last_health,metrics=brain.last_metrics)
                        send("idle")
                        if not checkpoint():
                            continue
                    elif plan is not None:
                        brain.clear_context()
                    if plan is None:
                        send("event", event=Event(kind="TaskStateChanged", request_id=req.request_id,
                             generation=req.generation, state=TaskState.AWAITING_CLARIFICATION).model_dump(mode="json"))
                        message = routing.message + (" Suggestions: " + ", ".join(routing.choices) if routing.choices else "")
                        code = "CLARIFICATION"
                        status = "failed"
                        if model_error:
                            message = recovery_message(model_error)
                            code = "TIMEOUT" if model_error == "TIMEOUT" else "COMPONENT_UNAVAILABLE"
                        elif isinstance(model_reply,Answer):
                            # Generated answer text is discarded; only registry-defined capabilities are displayed.
                            message,code,status = capabilities(settings.enabled_skills),"OK","succeeded"
                        elif isinstance(model_reply,Clarification):
                            message = "No action taken. " + model_reply.message
                            send("clarification",request_id=str(req.request_id),generation=req.generation,
                                 choices=list(model_reply.choices),origin=req.origin,expires_seconds=30)
                        elif model_reply is not None:
                            code,message = "UNSUPPORTED","No action taken. That request is outside the currently enabled capabilities. Ask ‘what can you do?’ for available actions."
                        outcome = Outcome(status=status, code=code, message=message, verification="local planner validation" if model_reply or model_error else "deterministic grammar")
                        record = HistoryEvent(request_id=req.request_id, origin=req.origin, status=status,
                            code=code, duration_ms=0, skill_id="controller.request")
                        if history is not None:
                            history.add(record)
                        send("action_result", request_id=str(req.request_id), generation=req.generation,
                             outcome=outcome.model_dump(mode="json"), finished=True)
                        continue
                    send("event", event=Event(kind="TaskStateChanged", request_id=req.request_id,
                         generation=req.generation, state=TaskState.EXECUTING).model_dump(mode="json"))
                    send("busy", timeout=sum(REGISTRY[step.skill].timeout for step in plan.steps) + 1)

                    def completed(record, outcome):
                        if history is not None:
                            history.add(record)
                        send("action_result", request_id=str(req.request_id), generation=req.generation,
                             skill=record.skill_id, outcome=outcome.model_dump(mode="json"), finished=False)

                    def confirm(resolved, request, step, valid):
                        def target_data():
                            if resolved.action.skill == "text.type":
                                return adapter.dictation.snapshot_data(resolved.target)
                            return {"address": engine.resolve(resolved.action).target}
                        target = target_data()
                        approval = approvals.issue(request, step, resolved.action, target)
                        send("event", event=Event(kind="TaskStateChanged", request_id=request.request_id,
                            generation=request.generation, state=TaskState.AWAITING_CONFIRMATION).model_dump(mode="json"))
                        send("busy", timeout=32)
                        send("confirmation", request_id=str(request.request_id), generation=request.generation,
                            token=approval.token, skill=resolved.action.skill,
                            text=resolved.action.arguments.text if resolved.action.skill=="text.type" else resolved.target,
                            destination=resolved.target.title if resolved.action.skill=="text.type" else "Your default browser")
                        accepted = False
                        try:
                            while valid() and time.monotonic() < approval.expires:
                                try:
                                    answer = Job.model_validate(commands.get(timeout=0.02))
                                except queue.Empty:
                                    continue
                                if answer.kind == "confirm":
                                    if answer.generation == request.generation and answer.confirmation_id == approval.token:
                                        accepted = answer.approved and approvals.consume(answer.confirmation_id, request, step, resolved.action, target_data())
                                        break
                                elif len(deferred) < 16:
                                    deferred.append(answer)
                        finally:
                            approvals.clear()
                            send("confirmation_closed", token=approval.token)
                        if valid():
                            send("event", event=Event(kind="TaskStateChanged", request_id=request.request_id,
                                generation=request.generation, state=TaskState.EXECUTING).model_dump(mode="json"))
                        return accepted and valid()

                    results = engine.execute(plan, req, checkpoint, completed, on_dispatch=lambda timeout: send("busy", timeout=timeout + 0.2), confirm=confirm)
                    if len(plan.steps)==1 and plan.steps[0].skill=="routine.run" and checkpoint():
                        count = sum(r.status in {"succeeded","unverified"} for r in results)
                        failed = any(r.status not in {"succeeded","unverified"} for r in results)
                        summary = Outcome(status="partial" if failed and count else ("failed" if failed else "succeeded"),
                            code="PARTIAL" if failed else "OK", message=f"Routine finished: {count} steps completed or handed off; {len(results)} attempted. Completed effects remain; failed steps were not retried.",verification="serial per-step results")
                        send("action_result",request_id=str(req.request_id),generation=req.generation,skill="routine.run",outcome=summary.model_dump(mode="json"),finished=False)
                    send("action_finished", request_id=str(req.request_id), generation=req.generation)
                    if history is not None:
                        history.prune(settings.history_days)
                        send("history", rows=history.list_recent())
                    send("idle")
                elif job.kind == "activate_model":
                    expected = job.generation
                    send("busy", timeout=15.3)
                    try:
                        brain.activate(settings,lambda: alive() and generation.value == expected)
                    except BrainError:
                        pass
                    send("model_status",message=brain.last_health,metrics={})
                    send("idle")
                elif job.kind == "import_catalog":
                    from autumn.winworker.cache import configure
                    configure(Path(root))
                    deadline = time.monotonic() + 15
                    expected = job.generation
                    send("busy", timeout=16)
                    imported = import_apps(lambda: alive() and generation.value == expected and time.monotonic() < deadline)
                    # Preserve owner-edited entries; newly discovered apps stay disabled/unreviewed.
                    previous = {entry.id: entry for entry in settings.apps}
                    for entry in imported:
                        previous.setdefault(entry.id, entry)
                    settings = settings.model_copy(update={"apps": tuple(previous.values())[:500]})
                    atomic_save(Path(root) / "config/settings.json", settings)
                    engine.settings = settings
                    send("settings_saved", settings=settings.model_dump(mode="json"))
                    send("idle")
                elif job.kind == "simulate" and job.request is not None:
                    req = job.request
                    # Fixed simulated latency exercises asynchronous cancellation; no input text needed.
                    for i in range(35):
                        if not alive():
                            return
                        if generation.value != req.generation:
                            break
                        if i == 10:
                            send("event", event=Event(kind="TaskStateChanged", request_id=req.request_id,
                                 generation=req.generation, state=TaskState.EXECUTING).model_dump(mode="json"))
                        stopping.wait(0.02)
                    else:
                        if generation.value == req.generation:
                            send("event", event=Event(kind="StepFinished", request_id=req.request_id,
                                 generation=req.generation, code="SIMULATED").model_dump(mode="json"))
                elif job.kind == "save_settings" and job.settings is not None:
                    atomic_save(Path(root) / "config/settings.json", job.settings)
                    settings = job.settings
                    brain.clear_context()
                    engine.settings = settings
                    if history is not None:
                        history.prune(settings.history_days)
                    send("settings_saved", settings=settings.model_dump(mode="json"))
                elif job.kind in {"history", "clear_history", "record"}:
                    if history is None:
                        raise RuntimeError("History unavailable")
                    if job.kind == "clear_history":
                        history.clear()
                    for record in job.records:
                        history.add(record)
                    history.prune(settings.history_days)
                    send("history", rows=history.list_recent())
                elif job.kind == "diagnostics":
                    send("diagnostics", rows=snapshot())
                elif job.kind == "dictation_targets":
                    send("dictation_targets", rows=adapter.dictation.enumerate())
                elif allow_faults and job.kind == "crash":
                    os._exit(23)
                elif allow_faults and job.kind == "hang":
                    while not stopping.wait(0.1):
                        pass
            except (OSError, ValueError, RuntimeError, sqlite3.Error, queue.Full):
                send("error", code="STORAGE_OR_COMPONENT_UNAVAILABLE")
                if job.kind == "execute" and job.request is not None:
                    send("event", event=Event(kind="TaskStateChanged", request_id=job.request.request_id,
                         generation=job.generation, state=TaskState.ERROR).model_dump(mode="json"))
                    send("action_finished", request_id=str(job.request.request_id), generation=job.generation)
                send("idle")
    finally:
        if history is not None:
            history.close()


class Supervisor:
    """poll() never waits. shutdown() is bounded and runs after the window closes."""
    def __init__(self, root: Path, *, heartbeat_timeout: float = 3.0, allow_faults: bool = False, worker_target=None, owned_job: bool = False) -> None:
        self.root = root
        self.context = get_context("spawn")
        self.generation = self.context.Value("L", 0)
        self.voice_generation = self.context.Value("L", 0)
        self.capture_gate = self.context.Value("b", False)
        self.heartbeat_timeout = heartbeat_timeout
        self.allow_faults = allow_faults
        self.worker_target = worker_target or worker_main
        self.use_job = owned_job
        self.job_handle = None
        self.process = None
        self.commands = None
        self.replies = None
        self.stopping = None
        self.restarts = 0
        self.disabled = False
        self.closed = False
        self.next_start = 0.0
        self.last_seen = 0.0
        self.started = 0.0
        self.retired: list = []
        self.busy_until = 0.0
        self.cancelled_at = 0.0
        self.start()

    def start(self) -> None:
        self.commands = self.context.Queue(maxsize=8)
        self.replies = self.context.Queue(maxsize=32)
        self.stopping = self.context.Event()
        self.process = self.context.Process(
            target=self.worker_target, args=(self.commands, self.replies, self.generation,
                                     self.stopping, str(self.root), self.allow_faults), daemon=True,
            kwargs=({'voice_generation':self.voice_generation} if self.worker_target is worker_main else
                    {'capture_gate':self.capture_gate} if self.use_job else {}),
        )
        self.process.start()
        if self.use_job:
            import win32job
            try:
                self.job_handle = win32job.CreateJobObject(None, "")
                limits = win32job.QueryInformationJobObject(self.job_handle,win32job.JobObjectExtendedLimitInformation)
                limits['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                win32job.SetInformationJobObject(self.job_handle,win32job.JobObjectExtendedLimitInformation,limits)
                win32job.AssignProcessToJobObject(self.job_handle,self.process.sentinel)
            except Exception:
                if self.job_handle is not None:
                    self.job_handle.Close()
                self.job_handle = None
                self.process.terminate()
                self.process.join(timeout=.5)
                raise RuntimeError('Cannot contain the owned speech worker') from None
        self.last_seen = self.started = time.monotonic()
        self.commands.put_nowait({'kind':'bootstrap','generation':self.generation.value})

    def submit(self, job: Job) -> bool:
        if self.closed or self.disabled or self.process is None:
            return False
        try:
            self.commands.put_nowait(job.model_dump(mode="python"))
            return True
        except queue.Full:
            return False

    def cancel(self, generation: int) -> None:
        self.generation.value = generation
        if self.busy_until:
            self.cancelled_at = time.monotonic()

    def cancel_voice(self):
        self.voice_generation.value+=1
        return self.voice_generation.value

    def restart(self):
        if self.closed:
            return
        self._retire()
        self.disabled=False
        self.restarts=0
        self.busy_until=self.cancelled_at=0
        self.next_start=time.monotonic()

    def _retire(self) -> None:
        if self.job_handle is not None:
            self.job_handle.Close()
            self.job_handle = None
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.retired.append(self.process)
        # Never wait on a queue feeder after a crashed reader.
        for channel in (self.commands, self.replies):
            channel.cancel_join_thread()
            channel.close()
        self.process = None

    def poll(self) -> list[dict]:
        if self.closed or self.disabled:
            return []
        now = time.monotonic()
        if self.process is None:
            if now >= self.next_start:
                self.start()
            return []
        messages = []
        for _ in range(32):
            try:
                message = self.replies.get_nowait()
            except queue.Empty:
                break
            self.last_seen = now
            if message["kind"] == "busy":
                self.busy_until = now + min(message["timeout"], 46)
            elif message["kind"] == "idle":
                self.busy_until = self.cancelled_at = 0.0
            elif message["kind"] != "heartbeat":
                messages.append(message)
        # A cold spawned process gets 10 seconds to import and bootstrap.
        overdue = ((now - self.last_seen > self.heartbeat_timeout and now - self.started > 10 and not self.busy_until)
                   or (self.busy_until and now > self.busy_until)
                   or (self.cancelled_at and now - self.cancelled_at > 0.5))
        if not self.process.is_alive() or overdue:
            self._retire()
            self.busy_until = self.cancelled_at = 0.0
            self.restarts += 1
            self.disabled = self.restarts >= 3
            self.next_start = now + min(0.25 * 2 ** (self.restarts - 1), 2.0)
            messages.append({"kind": "worker_failed", "disabled": self.disabled})
        # Reap without waiting on the presentation thread.
        for child in self.retired[:]:
            if not child.is_alive():
                child.join(timeout=0)
                child.close()
                self.retired.remove(child)
        return messages

    def shutdown(self) -> bool:
        if self.closed:
            return not self.retired
        self.closed = True
        if self.stopping is not None:
            self.stopping.set()
        if self.process is not None:
            self.process.join(timeout=1.0)
            self._retire()
        clean = True
        for child in self.retired:
            child.join(timeout=0.5)
            if child.is_alive():
                child.kill()
                child.join(timeout=0.5)
            clean = clean and not child.is_alive()
            if not child.is_alive():
                child.close()
        self.retired.clear()
        return clean
