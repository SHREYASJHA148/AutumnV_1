"""Lazy worker supervision; UI sees only bounded events and explicit user operations."""

from autumn.controller.worker import Supervisor
from autumn.speech.workers import (
    SpeechJob,
    capture_worker,
    playback_worker,
    recognition_worker,
)


class SpeechService:
    def __init__(self, root):
        self.root = root
        self.epoch = 0
        self.workers = {}
        self.want_devices = False

    def refresh_devices(self):
        if "capture" in self.workers:
            self.workers["capture"].restart()
            self.want_devices = True
        else:
            self.send("capture", "devices")

    def get(self, role):
        worker = self.workers.get(role)
        if worker is None:
            target = {
                "capture": capture_worker,
                "recognition": recognition_worker,
                "playback": playback_worker,
            }[role]
            worker = Supervisor(self.root, worker_target=target, owned_job=True)
            worker.cancel(self.epoch)
            self.workers[role] = worker
        return worker

    def send(self, role, kind, **fields):
        worker = self.get(role)
        if role == "capture" and kind in {"capture", "finish_capture"}:
            worker.capture_gate.value = kind == "capture"
        accepted = worker.submit(SpeechJob(kind=kind, generation=self.epoch, **fields))
        if not accepted and role == "capture":
            worker.capture_gate.value = False
        return accepted

    def cancel(self):
        self.epoch += 1
        for worker in self.workers.values():
            worker.capture_gate.value = False
            worker.cancel(self.epoch)

    def poll(self):
        messages = []
        for role, worker in self.workers.items():
            for message in worker.poll():
                if "generation" in message and message["generation"] != self.epoch:
                    continue
                if role == "capture" and message["kind"] == "speech_ready" and self.want_devices:
                    self.want_devices = False
                    worker.submit(SpeechJob(kind="devices", generation=self.epoch))
                messages.append({"role": role, **message})
        return messages

    def shutdown(self):
        self.cancel()
        return all([worker.shutdown() for worker in self.workers.values()])
