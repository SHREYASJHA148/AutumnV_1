"""Independent state machines with generation-based invalidation."""
from __future__ import annotations

from collections import deque

from autumn.controller.contracts import CaptureState as C
from autumn.controller.contracts import Event, Request
from autumn.controller.contracts import TaskState as T

CAPTURE_EDGES = {
    C.DISABLED: {C.PTT_READY, C.DEVICE_ERROR},
    C.PTT_READY: {C.DISABLED, C.RECORDING, C.SUSPENDED_PLAYBACK, C.DEVICE_ERROR},
    C.ARMED_WAKE: {C.DISABLED, C.RECORDING, C.SUSPENDED_PLAYBACK, C.DEVICE_ERROR},
    C.RECORDING: {C.DISABLED, C.PTT_READY, C.ARMED_WAKE, C.DEVICE_ERROR},
    C.SUSPENDED_PLAYBACK: {C.DISABLED, C.PTT_READY, C.ARMED_WAKE, C.DEVICE_ERROR},
    C.DEVICE_ERROR: {C.DISABLED, C.PTT_READY},
}
TASK_EDGES = {
    T.IDLE: {T.TRANSCRIBING, T.ROUTING, T.SPEAKING},
    T.TRANSCRIBING: {T.ROUTING, T.ERROR},
    T.ROUTING: {T.EXECUTING, T.AWAITING_CLARIFICATION, T.AWAITING_CONFIRMATION, T.ERROR},
    T.AWAITING_CLARIFICATION: {T.ROUTING, T.IDLE, T.ERROR},
    T.AWAITING_CONFIRMATION: {T.EXECUTING, T.IDLE, T.ERROR},
    T.EXECUTING: {T.SPEAKING, T.IDLE, T.ERROR, T.AWAITING_CONFIRMATION},
    T.SPEAKING: {T.IDLE, T.ERROR},
    T.CANCELLING: {T.IDLE},
    T.ERROR: {T.IDLE},
}


class Session:
    def __init__(self) -> None:
        self.capture = C.DISABLED
        self.task = T.IDLE
        self.generation = 0
        self.pending: deque[Request] = deque()
        self.active: Request | None = None
        self.suspended = False

    def set_capture(self, state: C) -> None:
        if state != self.capture and state not in CAPTURE_EDGES[self.capture]:
            raise ValueError("Invalid capture transition")
        self.capture = state

    def set_task(self, state: T) -> None:
        if state != self.task and state != T.CANCELLING and state not in TASK_EDGES[self.task]:
            raise ValueError("Invalid task transition")
        self.task = state

    def enqueue(self, origin: str = "typed", voice_generation: int = 0) -> Request | None:
        if self.suspended or (self.active is not None and len(self.pending) >= 5):
            return None
        request = Request(generation=self.generation, origin=origin,voice_generation=voice_generation)
        if self.active is None:
            self.active = request
            self.set_task(T.ROUTING)
        else:
            self.pending.append(request)
        return request

    def accepts(self, event: Event) -> bool:
        return (
            not self.suspended and event.generation == self.generation
            and self.active is not None and event.request_id == self.active.request_id
        )

    def begin_transcription(self,voice_generation=0):
        if self.suspended or self.active is not None or self.task!=T.IDLE:
            return None
        request=Request(generation=self.generation,origin='ptt_voice',voice_generation=voice_generation)
        self.active=request
        self.set_task(T.TRANSCRIBING)
        return request

    def finish(self) -> Request | None:
        self.set_task(T.IDLE)
        self.active = self.pending.popleft() if self.pending else None
        if self.active is not None:
            self.set_task(T.ROUTING)
        return self.active

    def stop(self) -> list[Request]:
        cancelled = ([self.active] if self.active else []) + list(self.pending)
        self.generation += 1
        self.set_task(T.CANCELLING)
        self.pending.clear()
        self.active = None
        self.capture = C.DISABLED if self.capture == C.ARMED_WAKE else (
            C.PTT_READY if self.capture not in {C.DISABLED, C.DEVICE_ERROR} else C.DISABLED
        )
        self.set_task(T.IDLE)
        return cancelled

    def suspend(self) -> list[Request]:
        cancelled = self.stop()
        self.capture = C.DISABLED
        self.suspended = True
        return cancelled

    def cancel_voice(self):
        removed=[request for request in self.pending if request.origin in {'ptt_voice','wake_voice'}]
        self.pending=deque(request for request in self.pending if request.origin not in {'ptt_voice','wake_voice'})
        promoted=None
        if self.active is not None and self.active.origin in {'ptt_voice','wake_voice'}:
            removed.insert(0,self.active)
            self.set_task(T.CANCELLING)
            self.set_task(T.IDLE)
            self.active=self.pending.popleft() if self.pending else None
            promoted=self.active
            if promoted is not None:
                self.set_task(T.ROUTING)
        return removed,promoted

    def resume(self) -> None:
        self.suspended = False
        self.capture = C.DISABLED
