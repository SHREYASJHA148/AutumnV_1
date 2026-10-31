from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication

from autumn.audio.calibration import Calibration, load, save
from autumn.audio.wake import profile
from autumn.controller.contracts import CaptureState
from autumn.ui.viewmodel import ViewModel


def accepted(**changes):
    values = dict(
        profile="a" * 64,
        trials=50,
        hits=45,
        negative_seconds=7200,
        false_triggers=2,
        cpu_window_seconds=300,
        cpu_percent=1,
        on_mains=True,
    )
    return Calibration(**{**values, **changes})


@pytest.mark.parametrize(
    "changes",
    [
        {"trials": 49},
        {"hits": 44},
        {"negative_seconds": 7199},
        {"false_triggers": 3},
        {"cpu_window_seconds": 299},
        {"cpu_percent": 5},
        {"on_mains": False},
    ],
)
def test_wake_acceptance_requires_every_measured_target(changes):
    assert not accepted(**changes).accepted
    assert accepted().accepted


def test_calibration_atomic_roundtrip_and_profile_binding(tmp_path):
    save(tmp_path, accepted())
    assert load(tmp_path) == accepted()
    assert profile("input", "endpoint", 0.5) != profile("input", "other", 0.5)
    assert profile("input", "endpoint", 0.5) != profile("input", "endpoint", 0.6)
    assert profile("input", "endpoint", 0.5) != profile("new-input", "endpoint", 0.5)


class Worker:
    def __init__(self):
        self.jobs = []
        self.messages = []
        self.capture_gate = SimpleNamespace(value=False)
        self.voice_generation = SimpleNamespace(value=0)

    def submit(self, job):
        self.jobs.append(job)
        return True

    def poll(self):
        messages, self.messages = self.messages, []
        return messages

    def cancel(self, generation):
        self.generation = generation

    def cancel_voice(self):
        self.voice_generation.value += 1

    def shutdown(self):
        return True


def viewmodel():
    app = QCoreApplication.instance() or QCoreApplication([])
    assert app
    vm = ViewModel(Worker())
    vm.ready = True
    return vm


def test_wake_never_arms_without_calibration_and_starts_off():
    vm = viewmodel()
    try:
        assert vm.wake.worker is None and not vm.wake.enabled
        vm.wake.arm()
        assert vm.wake.worker is None and not vm.wake.enabled
        assert vm.session.capture == CaptureState.DISABLED
    finally:
        vm.shutdown()


def test_stop_lock_and_microphone_off_disarm_without_recognizer():
    vm = viewmodel()
    worker = Worker()
    vm.wake.worker = worker
    try:
        for stop in (vm.stop, vm.suspend, vm.voice.toggleEnabled):
            vm.resume()
            vm.wake.enabled = True
            vm.wake.monitoring = True
            vm.session.capture = CaptureState.ARMED_WAKE
            worker.capture_gate.value = True
            stop()
            assert not vm.wake.enabled and not vm.wake.monitoring and not worker.capture_gate.value
            assert vm.session.capture == CaptureState.DISABLED
    finally:
        vm.shutdown()


def test_wake_uses_restricted_origin_and_never_dictation(monkeypatch):
    vm = viewmodel()
    worker = Worker()
    vm.wake.worker = worker
    sent = []
    monkeypatch.setattr(vm.voice, "send", lambda role, kind, **kw: sent.append((kind, kw)) or True)
    try:
        vm.wake.record = accepted()
        vm.wake.arm()
        operation = str(vm.wake.operation)
        worker.messages = [
            {
                "kind": "wake_listening",
                "generation": vm.wake.epoch,
                "operation_id": operation,
                "profile": "a" * 64,
            },
            {"kind": "wake_detected", "generation": vm.wake.epoch, "operation_id": operation},
        ]
        vm.wake.poll()
        assert vm.voice.purpose == "wake" and vm.voice.recording
        # Reserve a wake transcript directly; the worker policy independently denies typing/URLs.
        request = vm.session.begin_transcription(origin="wake_voice")
        assert request.origin == "wake_voice"
        from autumn.policy.matrix import decide

        assert decide("text.type", request.origin).outcome == "deny"
        assert decide("website.open", request.origin, registered_site=False).outcome == "deny"
    finally:
        vm.shutdown()


def test_playback_waits_until_wake_stream_is_closed(monkeypatch):
    vm = viewmodel()
    worker = Worker()
    vm.wake.worker = worker
    from uuid import uuid4

    vm.wake.operation = uuid4()
    vm.wake.monitoring = True
    vm.wake.enabled = True
    sent = []
    monkeypatch.setattr(vm.voice, "send", lambda role, kind, **kw: sent.append(kind) or True)
    try:
        vm.voice.testVoice()
        assert vm.voice.delayed_playback and not sent and vm.wake.closing
        worker.messages = [
            {
                "kind": "wake_stopped",
                "generation": vm.wake.epoch - 1,
                "operation_id": str(vm.wake.operation),
            }
        ]
        vm.wake.poll()
        assert not vm.voice.delayed_playback and sent == ["speak"]
    finally:
        vm.shutdown()


def test_startup_never_changes_unrelated_registry_entry(monkeypatch):
    from autumn.ui import desktop

    monkeypatch.setattr(desktop.sys, "frozen", True, raising=False)

    class Key:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(desktop.winreg, "CreateKeyEx", lambda *args: Key())
    monkeypatch.setattr(desktop.winreg, "QueryValueEx", lambda *args: ("unrelated app", 1))
    monkeypatch.setattr(
        desktop.winreg, "DeleteValue", lambda *args: pytest.fail("Must not delete unrelated value")
    )
    monkeypatch.setattr(
        desktop.winreg,
        "SetValueEx",
        lambda *args: pytest.fail("Must not overwrite unrelated value"),
    )
    with pytest.raises(ValueError):
        desktop.set_startup(False)
    with pytest.raises(ValueError):
        desktop.set_startup(True)
