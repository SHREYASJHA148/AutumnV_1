"""Supervised process boundary. Test faults cannot be enabled by UI input."""
from __future__ import annotations

import os
import queue
import sqlite3
import time
from multiprocessing import get_context
from pathlib import Path
from typing import Literal

from pydantic import Field

from autumn.controller.contracts import Contract, Event, HistoryEvent, Request, TaskState
from autumn.diagnostics.health import snapshot
from autumn.storage.history import HistoryStore
from autumn.storage.settings import Settings, atomic_save, load_settings


class Job(Contract):
    kind: Literal["bootstrap", "simulate", "save_settings", "history", "clear_history", "record", "diagnostics", "hang", "crash"]
    generation: int = Field(ge=0)
    request: Request | None = None
    settings: Settings | None = None
    records: tuple[HistoryEvent, ...] = ()


def worker_main(commands, replies, generation, stopping, root: str, allow_faults: bool) -> None:
    parent = os.getppid()
    history: HistoryStore | None = None
    settings = Settings()
    last_beat = 0.0

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
                job = Job.model_validate(commands.get(timeout=0.05))
            except queue.Empty:
                continue
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
                    send("ready", settings=settings.model_dump(mode="json"), code=code,
                         history=history.list_recent() if history is not None else [], diagnostics=snapshot())
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
                elif allow_faults and job.kind == "crash":
                    os._exit(23)
                elif allow_faults and job.kind == "hang":
                    while not stopping.wait(0.1):
                        pass
            except (OSError, ValueError, RuntimeError, sqlite3.Error, queue.Full):
                send("error", code="STORAGE_OR_COMPONENT_UNAVAILABLE")
    finally:
        if history is not None:
            history.close()


class Supervisor:
    """poll() never waits. shutdown() is bounded and runs after the window closes."""
    def __init__(self, root: Path, *, heartbeat_timeout: float = 3.0, allow_faults: bool = False) -> None:
        self.root = root
        self.context = get_context("spawn")
        self.generation = self.context.Value("L", 0)
        self.heartbeat_timeout = heartbeat_timeout
        self.allow_faults = allow_faults
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
        self.start()

    def start(self) -> None:
        self.commands = self.context.Queue(maxsize=8)
        self.replies = self.context.Queue(maxsize=32)
        self.stopping = self.context.Event()
        self.process = self.context.Process(
            target=worker_main, args=(self.commands, self.replies, self.generation,
                                     self.stopping, str(self.root), self.allow_faults), daemon=True,
        )
        self.process.start()
        self.last_seen = self.started = time.monotonic()
        self.submit(Job(kind="bootstrap", generation=self.generation.value))

    def submit(self, job: Job) -> bool:
        if self.closed or self.disabled or self.process is None:
            return False
        try:
            self.commands.put_nowait(job.model_dump(mode="json"))
            return True
        except queue.Full:
            return False

    def cancel(self, generation: int) -> None:
        self.generation.value = generation

    def _retire(self) -> None:
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
            if message["kind"] != "heartbeat":
                messages.append(message)
        # A cold spawned process gets 10 seconds to import and bootstrap.
        overdue = now - self.last_seen > self.heartbeat_timeout and now - self.started > 10
        if not self.process.is_alive() or overdue:
            self._retire()
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
