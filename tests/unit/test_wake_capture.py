import queue
import threading
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
import sounddevice

from autumn.audio import devices, wake
from autumn.audio.wake_worker import wake_worker
from autumn.winworker import cache


@pytest.mark.parametrize("mode", ["trigger", "overflow", "cancel"])
def test_injected_wake_closes_before_event_and_cleans_up(monkeypatch, tmp_path, mode):
    gate = SimpleNamespace(value=True)
    stream_state = []

    class Input:
        def __init__(self, **options):
            self.callback = options["callback"]
            self.active = False
            self.closed = False
            stream_state.append(self)

        def start(self):
            self.active = True
            for _ in range(10 if mode == "overflow" else 2):
                self.callback(np.ones((1280, 1), dtype=np.float32) * 0.01, 1280, None, None)
            if mode == "cancel":
                gate.value = False

        def abort(self):
            self.active = False

        def close(self):
            self.closed = True

    class Detector:
        def __init__(self, *args):
            self.count = 0

        def reset(self):
            pass

        def predict(self, frame):
            self.count += 1
            return 1.0, self.count >= 2

    class Replies(queue.Queue):
        def put(self, value, *args, **kwargs):
            if value["kind"] == "wake_detected":
                assert stream_state[0].closed
            return super().put(value, *args, **kwargs)

    monkeypatch.setattr(sounddevice, "InputStream", Input)
    monkeypatch.setattr(wake, "Detector", Detector)
    monkeypatch.setattr(
        devices, "resolve_device", lambda *args: {"id": "fixed", "rate": 16000, "index": 0}
    )
    monkeypatch.setattr(devices, "default_endpoint", lambda kind: None)
    monkeypatch.setattr(cache, "configure", lambda root: None)
    commands = queue.Queue()
    replies = Replies()
    stopping = threading.Event()
    thread = threading.Thread(
        target=wake_worker,
        args=(commands, replies, SimpleNamespace(value=0), stopping, str(tmp_path), False),
        kwargs={"capture_gate": gate},
        daemon=True,
    )
    thread.start()
    commands.put({"kind": "listen", "generation": 0, "operation_id": uuid4(), "mode": "calibrate"})
    events = []
    try:
        while True:
            event = replies.get(timeout=3)
            events.append(event)
            if event["kind"] == "wake_stopped":
                break
        assert all(s.closed for s in stream_state)
        assert any(e["kind"] == "wake_detected" for e in events) == (mode == "trigger")
        assert any(e["kind"] == "wake_error" for e in events) == (mode == "overflow")
    finally:
        stopping.set()
        thread.join(timeout=2)
    assert not thread.is_alive() and not list(tmp_path.iterdir())
