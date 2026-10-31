"""Real-time mixed-use trial; public inputs, no hardware capture/playback."""

import json
import time

from PySide6.QtCore import QObject, QTimer

from autumn.actions.catalog import FolderEntry
from autumn.actions.routines import Routine
from autumn.actions.schemas import Capabilities
from autumn.controller.worker import Job
from autumn.diagnostics.resources import owned_pids, sample
from autumn.speech.service import SpeechService


class Soak(QObject):
    def __init__(self, app, window, vm, report, seconds, launch_stamp=None):
        super().__init__()
        self.app, self.window, self.vm, self.report = app, window, vm, report
        self.duration = seconds
        self.start = time.monotonic()
        self.start_perf = time.perf_counter()
        self.launch_stamp = launch_stamp
        self.ready_at = None
        self.cycle = 0
        self.configured = False
        self.requested_config = False
        self.next_cycle = self.start
        self.next_write = self.start
        self.failures = []
        self.peak_mb = 0.0
        self.samples = 0
        self.counts = {
            "help": 0,
            "file_search": 0,
            "routine": 0,
            "stop_queue": 0,
            "expected_worker_crash": 0,
            "speech_synthetic": 0,
            "local_model_checks": 0,
        }
        self.speech = SpeechService(vm.supervisor.root / "soak-speech")
        self.speech_phase = None
        self.speech_deadline = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.window.hide()

    def record(self, final=False):
        now = time.monotonic()
        self.report.parent.mkdir(parents=True, exist_ok=True)
        self.report.write_text(
            json.dumps(
                {
                    "scope": "software mixed-use: typed help, disposable filenames, routines, Stop/queue, controlled crash, local model checks, synthetic speech; hidden UI; NO microphone/speaker trial",
                    "requested_seconds": self.duration,
                    "elapsed_seconds": round(now - self.start, 2),
                    "complete": final,
                    "two_hour_duration_met": now - self.start >= 7200,
                    "passed": final and not self.failures and self.cycle > 0,
                    "launch_to_typed_ready_seconds": self.ready_at,
                    "cycles": self.cycle,
                    "counts": self.counts,
                    "failures": self.failures[-20:],
                    "resource_samples": self.samples,
                    "peak_aggregate_owned_working_mb": round(self.peak_mb, 1),
                    "model_runtime_memory_included": False,
                    "gpu_profile_measured": False,
                    "audio_hardware_opened": False,
                    "raw_audio_or_transcripts_saved": False,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def tick(self):
        try:
            self.step()
        except Exception as error:
            self.failures.append({"stage": "controller", "type": type(error).__name__})
            self.finish()

    def step(self):
        now = time.monotonic()
        if (
            self.vm.wake.enabled
            or self.vm.wake.monitoring
            or self.vm.voice.recording
            or len(self.vm.session.pending) > 5
        ):
            raise RuntimeError("Invalid trial state")
        if self.ready_at is None and now - self.start > 20:
            raise TimeoutError("No typed readiness")
        if not self.requested_config and self.vm.ready:
            folder = self.vm.supervisor.root / "disposable filenames é"
            folder.mkdir(parents=True, exist_ok=True)
            for i in range(8):
                (folder / f"autumn-{i:02}.txt").write_text("public fixture", encoding="utf-8")
            routine = Routine(
                id="local-status", name="Local status", steps=(Capabilities(), Capabilities())
            )
            self.vm.update_settings(
                model_enabled=False,
                enabled_skills=("help.capabilities", "files.search", "routine.run"),
                folders=[
                    FolderEntry(id="soak", name="Soak", path=str(folder), search=True).model_dump()
                ],
                routines=[routine.model_dump(mode="json")],
            )
            self.requested_config = True
            self.ready_at = round(time.perf_counter() - (self.launch_stamp or self.start_perf), 3)
        if self.requested_config and not self.vm.settings_pending and self.vm.settings.routines:
            self.configured = True
        for event in self.speech.poll():
            if event["kind"] == "synthesized":
                import numpy as np

                from autumn.audio.buffer import normalize

                converted = normalize(
                    np.frombuffer(event["pcm"], dtype="<f4"), event["sample_rate"]
                )
                self.speech.send(
                    "recognition",
                    "transcribe",
                    pcm=converted.astype("<f4").tobytes(),
                    model_key="small.en",
                    assets_root=self.vm.settings.speech_assets_dir,
                )
                converted.fill(0)
                self.speech_phase = "recognize"
            elif event["kind"] == "recognized":
                if not event["result"]["accepted"]:
                    self.failures.append(
                        {"stage": "synthetic_speech", "code": event["result"]["code"]}
                    )
                else:
                    self.counts["speech_synthetic"] += 1
                self.speech_phase = None
            elif event["kind"] in {"worker_failed", "speech_error"}:
                self.failures.append({"stage": "speech_worker", "type": event["kind"]})
                self.speech_phase = None
        if self.speech_phase and now > self.speech_deadline:
            self.failures.append({"stage": "synthetic_speech", "type": "Timeout"})
            self.speech.cancel()
            self.speech_phase = None
        if (
            self.configured
            and self.vm.ready
            and self.vm.session.active is None
            and now >= self.next_cycle
        ):
            task = self.cycle % 8
            if task == 0:
                self.vm.submit("help")
                self.counts["help"] += 1
            elif task == 1:
                self.vm.submit("find text autumn in Soak")
                self.counts["file_search"] += 1
            elif task == 2:
                self.vm.submit("run routine Local status")
                self.counts["routine"] += 1
            elif task == 3:
                for _ in range(6):
                    self.vm.submit("help")
                self.vm.stop()
                self.counts["stop_queue"] += 1
            elif task == 4 and not self.speech_phase:
                self.speech.send(
                    "playback",
                    "synthesize",
                    text="What can you do?",
                    assets_root=self.vm.settings.speech_assets_dir,
                )
                self.speech_phase = "synthesize"
                self.speech_deadline = now + 40
            elif task == 5 and not self.counts["expected_worker_crash"]:
                self.vm.supervisor.submit(Job(kind="crash", generation=self.vm.session.generation))
                self.counts["expected_worker_crash"] += 1
            elif task == 6 and self.cycle % 48 == 6:
                self.vm.checkLocalBrain()
                self.counts["local_model_checks"] += 1
            else:
                self.window.setProperty("page", (self.cycle // 8) % 10)
            self.cycle += 1
            self.next_cycle = now + 15
        if now >= self.next_write:
            values = [value for pid in owned_pids(self.vm, self.speech) if (value := sample(pid))]
            self.peak_mb = max(self.peak_mb, sum(v["working_mb"] for v in values))
            self.samples += 1
            self.record()
            self.next_write = now + 5
        if (
            now - self.start >= self.duration
            and self.vm.session.active is None
            and not self.speech_phase
        ):
            self.finish()

    def finish(self):
        self.timer.stop()
        self.vm.stop()
        self.speech.shutdown()
        self.record(final=True)
        self.app.quit()
