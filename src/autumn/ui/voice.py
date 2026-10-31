"""User-gesture capture, half duplex and transient transcript presentation."""

from __future__ import annotations

import time
from uuid import uuid4

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from autumn.controller.contracts import CaptureState as C
from autumn.controller.contracts import TaskState as T
from autumn.speech.service import SpeechService

MESSAGES = {
    "SILENT_CAPTURE": "Microphone delivered silence. Check Windows Settings → Privacy & security → Microphone → desktop apps, the device mute, and the selected input.",
    "NO_SPEECH": "No clear speech detected. Try a short English command nearer the microphone.",
    "LOW_CONFIDENCE": "Recognition was uncertain. Try again, or type the command.",
    "BUFFER_OVERFLOW": "Recording buffer filled or audio overran. Audio discarded; try a shorter command.",
    "DEVICE_UNAVAILABLE": "Audio device unavailable or changed. Refresh devices and select the input again.",
    "COMPONENT_UNAVAILABLE": "Speech component unavailable. Check the local model files or selected device; typed commands remain available.",
    "CANCELLED": "Voice work stopped. Pending audio was discarded.",
    "EMPTY_AUDIO": "No audio captured. Hold the control while speaking.",
}


class VoiceViewModel(QObject):
    changed = Signal()

    def __init__(self, host, root):
        super().__init__(host)
        self.host = host
        self.service = SpeechService(root)
        self.enabled = False
        self.recording = False
        self.recognizing = False
        self.playing = False
        self.capture_id = None
        self.recognition_id = None
        self.playback_id = None
        self.capture_global = 0
        self.purpose = "command"
        self.rows = []
        self.level = 0.0
        self.seconds = 0.0
        self.transcript = ""
        self.status = "Microphone off. Choose a device, test it, then enable voice."
        self.test_pcm = b""
        self.tail_until = 0.0
        self.pending_reply = ""
        self.assets_status = "Local speech files not checked yet."
        self.diagnostics_preview = ""
        self.microphone_checked = False

    @Property(bool, notify=changed)
    def enabledVoice(self):
        return self.enabled

    @Property(bool, notify=changed)
    def isRecording(self):
        return self.recording

    @Property(bool, notify=changed)
    def isBusy(self):
        return (
            self.recording or self.recognizing or self.playing or time.monotonic() < self.tail_until
        )

    @Property(float, notify=changed)
    def inputLevel(self):
        return self.level

    @Property(str, notify=changed)
    def statusText(self):
        return self.status

    @Property(str, notify=changed)
    def lastTranscript(self):
        return self.transcript

    @Property(bool, notify=changed)
    def hasTestRecording(self):
        return bool(self.test_pcm)

    @Property("QVariantList", notify=changed)
    def inputDevices(self):
        return [{"id": "", "label": "System default input"}] + [
            r for r in self.rows if r["kind"] == "input"
        ]

    @Property("QVariantList", notify=changed)
    def outputDevices(self):
        return [{"id": "", "label": "System default output"}] + [
            r for r in self.rows if r["kind"] == "output"
        ]

    @Property(str, notify=changed)
    def mode(self):
        return self.host.settings.capture_mode

    @Property(str, notify=changed)
    def inputId(self):
        return self.host.settings.input_device_id

    @Property(str, notify=changed)
    def outputId(self):
        return self.host.settings.output_device_id

    @Property(str, notify=changed)
    def recognitionModel(self):
        return self.host.settings.recognition_model

    @Property(float, notify=changed)
    def volume(self):
        return self.host.settings.speech_volume

    @Property(float, notify=changed)
    def rate(self):
        return self.host.settings.speech_rate

    @Property(bool, notify=changed)
    def spokenReplies(self):
        return self.host.settings.speech_output_enabled

    @Property(str, notify=changed)
    def assetsStatus(self):
        return self.assets_status

    @Property(str, notify=changed)
    def diagnosticsPreview(self):
        return self.diagnostics_preview

    @Slot()
    def previewDiagnostics(self):
        import json
        self.diagnostics_preview = json.dumps({
            "application": "Autumn 0.4.0", "local_brain": self.host.modelStatus,
            "speech_files": self.assets_status,
            "audio_endpoints": {kind: sum(row["kind"] == kind for row in self.rows) for kind in ("input", "output")},
            "microphone_signal": "received" if self.microphone_checked else "not tested",
            "owner_speech_acceptance": "pending", "gpu_acceptance": "unverified",
            "bluetooth_trial": "unavailable", "microphone_enabled_at_start": False,
            "audio_saved": False, "transcripts_exported": False,
        }, indent=2)
        self.changed.emit()

    @Slot()
    def exportDiagnostics(self):
        if not self.diagnostics_preview:
            return
        from autumn.actions.catalog import local_path, no_reparse
        path, _ = QFileDialog.getSaveFileName(None, "Export the previewed diagnostics", "Autumn diagnostics.json", "JSON (*.json)")
        if path:
            try:
                chosen = local_path(path)
                no_reparse(chosen.parent)
                if chosen.exists():
                    no_reparse(chosen)
                chosen.write_text(self.diagnostics_preview, encoding="utf-8")
                self.status = "Previewed diagnostics exported."
            except (OSError, ValueError):
                self.status = "Could not export diagnostics to that local file."
            self.changed.emit()

    def send(self, role, kind, **fields):
        try:
            if self.service.send(role, kind, **fields):
                return True
        except (OSError, RuntimeError, ValueError):
            pass
        self.status = MESSAGES["COMPONENT_UNAVAILABLE"]
        self.changed.emit()
        return False

    @Slot()
    def refreshDevices(self):
        if self.isBusy:
            return
        try:
            self.service.refresh_devices()
        except (OSError, RuntimeError):
            self.status = MESSAGES["COMPONENT_UNAVAILABLE"]
            self.changed.emit()

    def cancel_voice_requests(self):
        active = self.host.session.active
        uncertain = self.host.session.task == T.EXECUTING
        if hasattr(self.host.supervisor, "cancel_voice"):
            self.host.supervisor.cancel_voice()
        removed, promoted = self.host.session.cancel_voice()
        records = []
        for request in removed:
            self.host.pending_inputs.pop(str(request.request_id), None)
            records.append(
                self.host.record(
                    request,
                    "partial" if request == active and uncertain else "cancelled",
                    "CANCELLED",
                )
            )
        self.host.persist(tuple(records))
        if promoted is not None:
            self.host.dispatch_request(promoted)
        if self.host.clarification_origin in {"ptt_voice", "wake_voice"}:
            self.host.clarification_choices.clear()

    def cancel(self, *, disable=False):
        was_playing = self.playing
        self.service.cancel()
        self.capture_id = self.recognition_id = self.playback_id = None
        self.recording = self.recognizing = self.playing = False
        self.test_pcm = b""
        self.level = 0
        self.pending_reply = ""
        if disable:
            self.enabled = False
        self.tail_until = (
            time.monotonic() + self.host.settings.acoustic_tail_ms / 1000 if was_playing else 0
        )
        if self.host.session.task == T.SPEAKING and self.host.session.active is None:
            self.host.session.set_task(T.IDLE)
        self.host.session.capture = (
            C.DISABLED
            if not self.enabled
            else (C.SUSPENDED_PLAYBACK if was_playing else C.PTT_READY)
        )
        self.changed.emit()

    @Slot()
    def toggleEnabled(self):
        if self.enabled or self.recording or self.recognizing:
            self.cancel_voice_requests()
            self.cancel(disable=True)
            self.status = "Microphone off. Voice-derived pending work discarded."
        elif not self.host.session.suspended:
            self.enabled = True
            if self.playing or time.monotonic() < self.tail_until:
                self.host.session.capture = C.SUSPENDED_PLAYBACK
                self.status = "Voice enabled. Recording stays suspended until playback and its acoustic tail finish."
            else:
                self.host.session.set_capture(C.PTT_READY)
                self.status = "Ready. Microphone opens only while you hold the control, or after a recording toggle."
        self.host.changed.emit()
        self.changed.emit()

    @Slot()
    def beginHold(self):
        if self.mode == "hold":
            self.begin()

    @Slot()
    def endHold(self):
        if self.mode == "hold":
            self.finishCapture()

    @Slot()
    def toggleRecording(self):
        if self.recording:
            self.finishCapture()
        elif self.enabled:
            self.begin()

    @Slot()
    def testMicrophone(self):
        self.begin(test=True)

    def begin(self, test=False):
        if (
            not self.host.canSend
            or self.host.session.active is not None
            or self.isBusy
            or (not test and not self.enabled)
        ):
            self.status = (
                "Enable voice and wait for the current task or playback to finish before recording."
            )
            self.changed.emit()
            return
        self.capture_id = uuid4()
        self.capture_global = self.host.session.generation
        self.purpose = "test" if test else "command"
        self.test_pcm = b""
        self.transcript = ""
        self.recording = True
        self.seconds = 0
        self.host.session.capture = C.RECORDING
        self.status = (
            "Opening microphone for a four-second test…"
            if test
            else "Recording… release to finish. Limit 20 seconds."
        )
        if not self.send(
            "capture",
            "capture",
            operation_id=self.capture_id,
            device_id=self.inputId,
            seconds=4 if test else 20,
            endpoint=not test and self.mode == "toggle",
        ):
            self.recording = False
            self.capture_id = None
            self.host.session.capture = C.DEVICE_ERROR
        self.host.changed.emit()
        self.changed.emit()

    @Slot()
    def finishCapture(self):
        if self.recording and self.capture_id:
            self.send("capture", "finish_capture", operation_id=self.capture_id)

    def on_typed_input(self):
        if self.recording or self.recognizing:
            self.cancel_voice_requests()
            self.cancel()
        if self.playing:
            self.cancel()

    @Slot(str, str, str, str, float, float, bool)
    def saveOptions(self, input_id, output_id, mode, model, volume, rate, replies):
        if self.isBusy or not self.host.canConfigure:
            return
        self.host.update_settings(
            input_device_id=input_id,
            output_device_id=output_id,
            capture_mode=mode,
            recognition_model=model,
            speech_volume=volume,
            speech_rate=rate,
            speech_output_enabled=replies,
        )
        self.host.shortcutsChanged.emit()

    @Slot()
    def chooseModels(self):
        if self.isBusy or not self.host.canConfigure:
            return
        path = QFileDialog.getExistingDirectory(None, "Select local speech models folder")
        if path:
            from autumn.actions.catalog import local_path, no_reparse

            try:
                chosen = local_path(path)
                no_reparse(chosen)
            except (OSError, ValueError):
                self.status = "Choose a local folder without links or network paths."
                self.changed.emit()
                return
            self.host.update_settings(speech_assets_dir=str(chosen))

    @Slot()
    def testVoice(self):
        self.speak("Hello. I am Autumn, your local assistant.")

    @Slot()
    def checkModels(self):
        if not self.isBusy:
            self.assets_status = "Checking local model sizes and checksums…"
            self.send(
                "recognition",
                "health",
                model_key=self.recognitionModel,
                assets_root=self.host.settings.speech_assets_dir,
            )
            self.changed.emit()

    @Slot()
    def playTestRecording(self):
        if self.test_pcm and not self.isBusy:
            self.start_playback("play_pcm", pcm=self.test_pcm, sample_rate=16000)

    def speak(self, text):
        if (
            not self.recording
            and not self.recognizing
            and not self.playing
            and not self.host.session.suspended
        ):
            self.start_playback("speak", text=text)

    def start_playback(self, kind, **fields):
        self.playback_id = uuid4()
        self.playing = True
        self.host.session.capture = C.SUSPENDED_PLAYBACK if self.enabled else C.DISABLED
        if self.host.session.active is None and self.host.session.task == T.IDLE:
            self.host.session.set_task(T.SPEAKING)
        self.status = "Speaking; recording is suspended. Use Stop to silence playback."
        if not self.send(
            "playback",
            kind,
            operation_id=self.playback_id,
            device_id=self.outputId,
            assets_root=self.host.settings.speech_assets_dir,
            volume=self.volume,
            rate=self.rate,
            **fields,
        ):
            self.playing = False
            self.playback_id = None
            self.host.session.capture = C.PTT_READY if self.enabled else C.DISABLED
            if self.host.session.task == T.SPEAKING:
                self.host.session.set_task(T.IDLE)
        self.changed.emit()
        self.host.changed.emit()

    def action_result(self, message):
        active = self.host.session.active
        if active is not None and active.origin == "ptt_voice" and self.spokenReplies:
            self.pending_reply = message

    def action_finished(self):
        text = self.pending_reply
        self.pending_reply = ""
        if text:
            self.speak(text)

    def poll(self):
        if self.tail_until and time.monotonic() >= self.tail_until:
            self.tail_until = 0
            self.host.session.capture = C.PTT_READY if self.enabled else C.DISABLED
            self.changed.emit()
            self.host.changed.emit()
        for event in self.service.poll():
            kind = event["kind"]
            if kind == "devices":
                self.rows = event["rows"]
                self.status = (
                    "Devices refreshed. Select the built-in microphone and test it explicitly."
                )
            elif kind == "speech_health":
                ready = all(event["verified"].values())
                self.assets_status = (
                    "Speech model and female voice verified locally."
                    if ready
                    else "Some speech files are missing or corrupt. Choose a verified local models folder."
                ) + f" Free storage: {event['free_gb']} GB."
            elif kind == "level":
                self.level = event["value"]
                self.seconds = event["seconds"]
                if self.seconds >= 17:
                    self.status = "Recording will end at 20 seconds; finish the command now."
            elif (
                kind == "captured"
                and self.capture_id is not None
                and event["operation_id"] == str(self.capture_id)
            ):
                self.recording = False
                self.level = 0
                self.capture_id = None
                self.host.session.capture = C.PTT_READY if self.enabled else C.DISABLED
                if self.capture_global != self.host.session.generation:
                    continue
                if self.purpose == "command":
                    counter = getattr(self.host.supervisor, "voice_generation", None)
                    request = self.host.session.begin_transcription(
                        counter.value if counter is not None else 0
                    )
                    if request is None:
                        continue
                    self.recognition_id = request.request_id
                    self.host.started_requests[str(request.request_id)] = time.monotonic()
                else:
                    self.recognition_id = uuid4()
                    self.test_pcm = event["pcm"]
                self.recognizing = True
                self.status = "Recognizing English locally…"
                if not self.send(
                    "recognition",
                    "transcribe",
                    operation_id=self.recognition_id,
                    pcm=event["pcm"],
                    model_key=self.recognitionModel,
                    assets_root=self.host.settings.speech_assets_dir,
                ):
                    self.recognizing = False
                    self.cancel_voice_requests()
            elif (
                kind == "recognized"
                and self.recognition_id is not None
                and event["operation_id"] == str(self.recognition_id)
            ):
                self.recognizing = False
                self.recognition_id = None
                result = event["result"]
                if result["accepted"]:
                    self.microphone_checked = True
                    self.transcript = result["text"]
                    self.status = "Recognized text is visible. Edit and send as text if needed."
                    if self.purpose == "command":
                        active = self.host.session.active
                        if (
                            active is not None
                            and active.origin == "ptt_voice"
                            and active.generation == self.capture_global
                        ):
                            if self.host.advanced.arm_dictation:
                                self.host.advanced.route_voice(active, self.transcript)
                                continue
                            self.host.session.set_task(T.ROUTING)
                            self.host.append("You (voice)", self.transcript)
                            self.host.pending_inputs[str(active.request_id)] = self.transcript
                            self.host.dispatch_request(active)
                else:
                    self.status = MESSAGES.get(result["code"], MESSAGES["COMPONENT_UNAVAILABLE"])
                    if self.purpose == "command":
                        self.cancel_voice_requests()
            elif (
                kind == "capture_error"
                and self.capture_id is not None
                and event["operation_id"] == str(self.capture_id)
            ):
                self.recording = False
                self.capture_id = None
                self.level = 0
                self.host.session.capture = (
                    C.DEVICE_ERROR
                    if event["code"] == "DEVICE_UNAVAILABLE"
                    else (C.PTT_READY if self.enabled else C.DISABLED)
                )
                self.status = MESSAGES.get(event["code"], MESSAGES["COMPONENT_UNAVAILABLE"])
            elif (
                kind == "played"
                and self.playback_id is not None
                and event["operation_id"] == str(self.playback_id)
            ):
                self.playing = False
                self.playback_id = None
                self.tail_until = time.monotonic() + self.host.settings.acoustic_tail_ms / 1000
                self.status = (
                    "Playback finished; allowing a short acoustic tail before voice readiness."
                )
                if self.host.session.task == T.SPEAKING and self.host.session.active is None:
                    self.host.session.set_task(T.IDLE)
            elif kind in {"speech_error", "worker_failed"}:
                if kind == "speech_error" and event.get("operation_id") not in {
                    str(self.capture_id),
                    str(self.recognition_id),
                    str(self.playback_id),
                    "None",
                }:
                    continue
                self.status = MESSAGES["COMPONENT_UNAVAILABLE"]
                self.cancel_voice_requests()
                self.cancel(disable=True)
            self.changed.emit()
            self.host.changed.emit()

    def shutdown(self):
        self.cancel(disable=True)
        return self.service.shutdown()
