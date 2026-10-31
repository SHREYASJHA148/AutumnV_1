import time
from uuid import uuid4

from autumn.speech.service import SpeechService


def wait(service, kind, timeout=12):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        for event in service.poll():
            if event["kind"] == kind:
                return event
            assert event["kind"] not in {"worker_failed", "speech_error"}
        time.sleep(0.02)
    raise AssertionError("Speech worker timeout")


def test_owned_worker_binary_ipc_silence_and_no_audio_files(tmp_path):
    service = SpeechService(tmp_path / "speech é")
    try:
        operation = uuid4()
        assert service.send("recognition", "transcribe", operation_id=operation, pcm=b"\0" * 64000)
        event = wait(service, "recognized")
        assert not event["result"]["accepted"] and event["result"]["code"] == "SILENT_CAPTURE"
        assert event["operation_id"] == str(operation)
        assert service.workers["recognition"].job_handle is not None
        service.cancel()
        # An old queued request must be refused after the shared epoch changes.
        worker = service.workers["recognition"]
        worker.commands.put_nowait({"kind": "transcribe", "generation": 0, "pcm": b"\0" * 64000})
        until = time.monotonic() + 0.25
        while time.monotonic() < until:
            assert not any(e["kind"] == "recognized" for e in service.poll())
            time.sleep(0.02)
    finally:
        assert service.shutdown()
    assert not list(tmp_path.rglob("*.wav")) and not list(tmp_path.rglob("*.pcm"))


def test_closing_owner_job_terminates_worker_and_does_not_replay(tmp_path):
    service = SpeechService(tmp_path)
    worker = service.get("recognition")
    try:
        wait(service, "speech_ready")
        worker.job_handle.Close()
        worker.job_handle = None
        event = wait_failure(service)
        assert event["role"] == "recognition"
        wait(service, "speech_ready")
        assert not any(event["kind"] == "recognized" for event in service.poll())
    finally:
        assert service.shutdown()


def wait_failure(service):
    until = time.monotonic() + 3
    while time.monotonic() < until:
        for event in service.poll():
            if event["kind"] == "worker_failed":
                return event
        time.sleep(0.02)
    raise AssertionError("Owned worker survived job closure")
