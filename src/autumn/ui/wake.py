"""Explicit opt-in only; calibration never dispatches commands or saves audio."""

import time
from uuid import uuid4

from PySide6.QtCore import Property, QObject, Signal, Slot

from autumn.audio.calibration import Calibration
from autumn.audio.wake_worker import WakeJob, wake_worker
from autumn.controller.contracts import CaptureState as C
from autumn.controller.worker import Supervisor


class WakeViewModel(QObject):
    changed = Signal()

    def __init__(self, host, root):
        super().__init__(host)
        self.host, self.root = host, root
        self.worker = None
        self.epoch = 0
        self.enabled = False
        self.monitoring = False
        self.closing = False
        self.operation = None
        self.mode = ""
        self.record = None
        self.since = 0.0
        self.trial_deadline = 0.0
        self.next_listen = 0.0
        self.score = 0.0
        self.status = "Wake is off. Pretrained phrase: “hey jarvis”. Autumn remains the assistant’s name. Calibration is required before arming."
        self.profile_settings = None
        host.settingsChanged.connect(self.settings_changed)

    @Property(bool, notify=changed)
    def enabledWake(self):
        return self.enabled

    @Property(bool, notify=changed)
    def listening(self):
        return self.monitoring

    @Property(bool, notify=changed)
    def busy(self):
        return self.monitoring or self.closing

    @Property(bool, notify=changed)
    def calibrated(self):
        return bool(self.record and self.record.accepted)

    @Property(str, notify=changed)
    def statusText(self):
        return self.status

    @Property(str, notify=changed)
    def progress(self):
        if not self.record:
            return (
                "No calibration results loaded. Wake is unavailable until the required trials pass."
            )
        seconds = self.record.negative_seconds + (
            time.monotonic() - self.since if self.mode == "negative" and self.since else 0
        )
        return f"{self.record.hits}/{self.record.trials} intentional detections (need 45/50); {seconds / 60:.1f}/120 minutes active household listening; {self.record.false_triggers} false wakes (maximum 2 in 120 minutes). CPU window: {self.record.cpu_window_seconds:.0f}/300 seconds, {self.record.cpu_percent:.2f}% normalized CPU on mains: {self.record.on_mains}."

    def get(self):
        if self.worker is None:
            self.worker = Supervisor(self.root, worker_target=wake_worker, owned_job=True)
            self.worker.cancel(self.epoch)
        return self.worker

    def send(self, kind, **fields):
        try:
            return self.get().submit(WakeJob(kind=kind, generation=self.epoch, **fields))
        except (OSError, RuntimeError, ValueError):
            self.status = "Wake component unavailable. Use hold-to-talk or typed commands."
            self.changed.emit()
            return False

    @Slot()
    def checkFiles(self):
        if not self.busy:
            self.send("check", assets_root=self.host.settings.speech_assets_dir)
            self.send("load_calibration")

    @Slot(float)
    def saveThreshold(self, threshold):
        if self.host.canConfigure:
            self.host.update_settings(wake_threshold=threshold)

    def settings_changed(self):
        key = (
            self.host.settings.input_device_id,
            self.host.settings.speech_assets_dir,
            self.host.settings.wake_threshold,
        )
        if self.profile_settings is not None and key != self.profile_settings:
            self.disarm()
            self.record = None
            self.status = "Audio device, model location or threshold changed. Load matching calibration or recalibrate."
        self.profile_settings = key
        self.changed.emit()

    def update_record(self, **fields):
        if self.record:
            self.record = Calibration.model_validate({**self.record.model_dump(), **fields})

    def account(self):
        if self.since and self.mode == "negative" and self.record:
            self.update_record(
                negative_seconds=min(
                    86400, self.record.negative_seconds + time.monotonic() - self.since
                )
            )
        self.since = 0.0

    def stop_listener(self):
        self.account()
        self.epoch += 1
        if self.worker:
            self.worker.capture_gate.value = False
            self.worker.cancel(self.epoch)
        self.closing = self.monitoring or self.closing
        self.monitoring = False
        self.trial_deadline = 0.0
        self.changed.emit()

    def pause(self):
        self.stop_listener()
        if self.mode == "positive":
            self.mode = ""

    @Slot()
    def disarm(self):
        self.enabled = False
        self.stop_listener()
        self.mode = ""
        self.status = "Wake off. Microphone closes; no wake request remains armed."
        if self.host.session.capture == C.ARMED_WAKE:
            self.host.session.capture = C.DISABLED
        self.host.changed.emit()
        self.changed.emit()

    def begin(self, mode):
        if (
            self.closing
            or self.monitoring
            or self.host.voice.isBusy
            or self.host.session.active is not None
            or not self.host.canSend
        ):
            self.status = (
                "Wait for current work, recording, playback and its acoustic tail to finish."
            )
            self.changed.emit()
            return
        self.mode = mode
        self.operation = uuid4()
        self.monitoring = True
        worker = self.get()
        worker.capture_gate.value = True
        if not self.send(
            "listen",
            operation_id=self.operation,
            mode="arm" if mode == "armed" else "calibrate",
            device_id=self.host.settings.input_device_id,
            assets_root=self.host.settings.speech_assets_dir,
            threshold=self.host.settings.wake_threshold,
        ):
            self.monitoring = False
        else:
            self.host.session.capture = C.ARMED_WAKE
            self.status = (
                "Opening wake microphone. Calibration mode never runs commands."
                if mode != "armed"
                else "Opening local wake listener. Say “hey jarvis”, pause, then give one command."
            )
        self.host.changed.emit()
        self.changed.emit()

    @Slot()
    def arm(self):
        if not self.calibrated:
            self.status = "Wake remains disabled: complete 50 intentional and 120 minutes of household-audio calibration first."
            self.changed.emit()
            return
        self.host.voice.cancel(disable=True)
        self.host.advanced.armDictation(False)
        self.enabled = True
        self.begin("armed")

    @Slot()
    def positiveTrial(self):
        if self.record and self.record.trials >= 50:
            self.status = "50 intentional attempts already recorded. Begin household-audio calibration next, or reset."
            self.changed.emit()
            return
        self.enabled = False
        self.host.voice.cancel(disable=True)
        self.begin("positive")

    @Slot()
    def negativeTrial(self):
        self.enabled = False
        self.host.voice.cancel(disable=True)
        self.begin("negative")

    @Slot()
    def resetCalibration(self):
        self.disarm()
        self.record = None
        self.status = (
            "Calibration reset in this session. Next attempt starts a new measured profile."
        )
        self.changed.emit()

    @Slot()
    def saveCalibration(self):
        self.disarm()
        if self.record:
            self.send("save_calibration", record=self.record.model_dump())

    def poll(self):
        now = time.monotonic()
        if self.trial_deadline and now >= self.trial_deadline:
            self.update_record(trials=self.record.trials + 1)
            self.stop_listener()
            self.mode = ""
            self.status = (
                "Intentional trial missed within five seconds. Press Next attempt to continue."
            )
        if (
            self.mode == "negative"
            and self.record
            and self.since
            and self.record.negative_seconds + now - self.since >= 7200
        ):
            self.saveCalibration()
        if self.worker:
            for event in self.worker.poll():
                kind = event["kind"]
                if kind == "wake_stopped" and event.get("operation_id") == str(self.operation):
                    self.closing = False
                    self.monitoring = False
                    if self.host.session.capture == C.ARMED_WAKE:
                        self.host.session.capture = C.DISABLED
                if "generation" in event and event["generation"] != self.epoch:
                    continue
                if kind == "wake_calibration":
                    self.record = (
                        Calibration.model_validate(event["record"]) if event["record"] else None
                    )
                    self.status = "Calibration loaded. Arming still requires a matching device/model/threshold profile."
                elif kind == "wake_checked":
                    self.status = "Pinned wake files verified locally. No microphone was opened."
                elif kind == "wake_listening" and event["operation_id"] == str(self.operation):
                    if self.record is None or self.record.profile != event["profile"]:
                        self.record = Calibration(profile=event["profile"])
                    self.since = now
                    self.trial_deadline = now + 5 if self.mode == "positive" else 0
                    self.status = (
                        "Listening for one intentional “hey jarvis” attempt; no commands."
                        if self.mode == "positive"
                        else (
                            "Household-audio calibration listening; commands disabled. Include normal speaker media."
                            if self.mode == "negative"
                            else "Wake listening locally: “hey jarvis”, pause, command."
                        )
                    )
                elif kind == "wake_score" and event["operation_id"] == str(self.operation):
                    self.score = event["score"]
                    if self.mode == "negative" and self.record and event["wall_seconds"] >= 300:
                        import os

                        self.update_record(
                            cpu_window_seconds=event["wall_seconds"],
                            cpu_percent=min(
                                100, event["cpu_one_core_percent"] / max(1, os.cpu_count() or 1)
                            ),
                            on_mains=event["on_mains"],
                        )
                elif kind == "wake_detected" and event["operation_id"] == str(self.operation):
                    mode = self.mode
                    self.account()
                    self.monitoring = False
                    self.trial_deadline = 0.0
                    self.next_listen = now + 4
                    if mode == "positive":
                        self.update_record(trials=self.record.trials + 1, hits=self.record.hits + 1)
                        self.mode = ""
                        self.status = "Intentional wake detected. Press Next attempt for another independent trial."
                    elif mode == "negative":
                        self.update_record(false_triggers=self.record.false_triggers + 1)
                    elif (
                        self.enabled
                        and self.host.session.active is None
                        and not self.host.voice.isBusy
                    ):
                        self.host.voice.begin(wake=True)
                elif kind in {"wake_error", "worker_failed"}:
                    self.enabled = False
                    self.account()
                    self.monitoring = self.closing = False
                    self.mode = ""
                    if self.host.voice.purpose == "wake" and (
                        self.host.voice.recording or self.host.voice.recognizing
                    ):
                        self.host.voice.cancel_voice_requests()
                        self.host.voice.cancel(disable=True)
                    if self.host.session.capture == C.ARMED_WAKE:
                        self.host.session.capture = C.DISABLED
                    self.status = "Wake unavailable or calibration/device changed. Refresh files/device and recalibrate; typed and hold-to-talk remain available."
                self.changed.emit()
                self.host.changed.emit()
        if self.host.voice.delayed_playback and not self.monitoring and not self.closing:
            kind, fields = self.host.voice.delayed_playback
            self.host.voice.delayed_playback = None
            self.host.voice.playing = False
            self.host.voice.start_playback(kind, **fields)
        if (
            not self.monitoring
            and not self.closing
            and now >= self.next_listen
            and not self.host.voice.isBusy
            and self.host.session.active is None
        ):
            if self.enabled:
                self.begin("armed")
            elif self.mode == "negative":
                self.begin("negative")

    def shutdown(self):
        self.disarm()
        return self.worker.shutdown() if self.worker else True
