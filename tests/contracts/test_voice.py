import time
from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtCore import QCoreApplication

from autumn.controller.contracts import CaptureState as C
from autumn.controller.contracts import TaskState as T
from autumn.ui.viewmodel import ViewModel


class Actions:
    def __init__(self):
        self.jobs = []
        self.voice_generation = SimpleNamespace(value=0)

    def submit(self, job):
        self.jobs.append(job)
        return True

    def poll(self):
        return []

    def cancel(self, generation):
        pass

    def cancel_voice(self):
        self.voice_generation.value += 1

    def shutdown(self):
        return True


class Speech:
    def __init__(self):
        self.messages = []
        self.sent = []
        self.epoch = 0

    def send(self, role, kind, **fields):
        self.sent.append((role, kind, fields))
        return True

    def cancel(self):
        self.epoch += 1

    def poll(self):
        messages, self.messages = self.messages, []
        return messages

    def shutdown(self):
        return True


def make_vm():
    app = QCoreApplication.instance() or QCoreApplication([])
    assert app
    vm = ViewModel(Actions())
    vm.voice.service = Speech()
    vm.ready = True
    return vm


def captured(vm):
    vm.voice.service.messages = [{"kind": "captured", "operation_id": str(vm.voice.capture_id),
                                  "pcm": b"\0" * 6400}]
    vm.poll()
    return vm.voice.recognition_id


def recognized(vm, operation):
    vm.voice.service.messages = [{"kind": "recognized", "operation_id": str(operation),
                                  "result": {"accepted": True, "text": "help"}}]
    vm.poll()


def test_voice_is_gesture_only_and_microphone_test_never_dispatches():
    vm = make_vm()
    try:
        assert not vm.voice.enabled and not vm.voice.service.sent
        vm.voice.beginHold()
        assert not vm.voice.service.sent
        vm.voice.testMicrophone()
        assert vm.voice.service.sent[-1][2]["seconds"] == 4
        operation = captured(vm)
        recognized(vm, operation)
        assert vm.voice.lastTranscript == "help"
        assert not any(job.kind == "execute" for job in vm.supervisor.jobs)
        assert vm.session.active is None
    finally:
        vm.shutdown()


def test_ptt_transcript_keeps_voice_origin_and_off_invalidates_stale_results():
    vm = make_vm()
    try:
        vm.toggleVoice()
        vm.voice.beginHold()
        operation = captured(vm)
        assert vm.session.task == T.TRANSCRIBING
        recognized(vm, operation)
        job = next(job for job in reversed(vm.supervisor.jobs) if job.kind == "execute")
        assert job.request.origin == "ptt_voice" and job.text == "help"
        vm.toggleVoice()
        assert vm.session.active is None and vm.session.capture == C.DISABLED
        count = len(vm.supervisor.jobs)
        recognized(vm, operation)
        assert len(vm.supervisor.jobs) == count
        assert vm.supervisor.voice_generation.value == 1
    finally:
        vm.shutdown()


def test_microphone_off_keeps_typed_work_and_cancels_voice_queue():
    vm = make_vm()
    try:
        vm.submit("help")
        typed = vm.session.active
        voice_request = vm.session.enqueue(origin="ptt_voice")
        vm.toggleVoice()
        vm.toggleVoice()
        assert vm.session.active == typed and voice_request not in vm.session.pending
        assert vm.session.generation == typed.generation
    finally:
        vm.shutdown()


def test_typed_input_cancels_transcription_and_remains_available_after_voice_error():
    vm = make_vm()
    try:
        vm.toggleVoice()
        vm.voice.beginHold()
        operation = captured(vm)
        vm.submit("help")
        assert vm.session.active.origin == "typed"
        recognized(vm, operation)
        assert len([job for job in vm.supervisor.jobs if job.kind == "execute"]) == 1
        vm.voice.service.messages = [{"kind": "worker_failed", "role": "recognition"}]
        vm.poll()
        assert vm.canSend and vm.session.active.origin == "typed"
    finally:
        vm.shutdown()


def test_playback_blocks_recording_until_tail_and_stop_discards_audio():
    vm = make_vm()
    try:
        vm.toggleVoice()
        vm.voice.testVoice()
        assert vm.session.task == T.SPEAKING and vm.session.capture == C.SUSPENDED_PLAYBACK
        count = len(vm.voice.service.sent)
        vm.voice.beginHold()
        assert len(vm.voice.service.sent) == count
        vm.voice.service.messages = [{"kind": "played", "operation_id": str(vm.voice.playback_id)}]
        vm.poll()
        vm.voice.beginHold()
        assert len(vm.voice.service.sent) == count
        vm.voice.tail_until = time.monotonic() - 1
        vm.poll()
        vm.voice.beginHold()
        assert vm.voice.isRecording
        old = vm.voice.capture_id
        vm.stop()
        vm.voice.service.messages = [{"kind": "captured", "operation_id": str(old), "pcm": b"\0" * 6400}]
        vm.poll()
        assert not vm.voice.recognizing and not vm.voice.test_pcm
    finally:
        vm.shutdown()


def test_stale_speech_error_does_not_cancel_new_recording():
    vm = make_vm()
    try:
        vm.toggleVoice()
        vm.voice.beginHold()
        vm.voice.service.messages = [{"kind": "speech_error", "operation_id": str(uuid4())}]
        vm.poll()
        assert vm.voice.isRecording and vm.voice.enabled
    finally:
        vm.shutdown()


def test_diagnostics_preview_excludes_transient_words_and_paths():
    vm = make_vm()
    try:
        vm.voice.transcript = "Private invented test words"
        vm.voice.previewDiagnostics()
        assert "Private" not in vm.voice.diagnosticsPreview
        assert "not tested" in vm.voice.diagnosticsPreview
        assert "transcripts_exported" in vm.voice.diagnosticsPreview
    finally:
        vm.shutdown()
