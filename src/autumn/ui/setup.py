"""Visible user-triggered setup; networking never begins automatically."""

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from autumn.controller.worker import Supervisor
from autumn.setup.worker import SetupJob, setup_worker
from autumn.speech.assets import default_models


class SetupViewModel(QObject):
    changed = Signal()

    def __init__(self, host, root):
        super().__init__(host)
        self.host, self.root = host, root
        self.worker = None
        self.epoch = 0
        self.rows = []
        self.busy = False
        self.fraction = 0.0
        self.free_gb = 0.0
        self.enough = False
        self.status = "Check the local runtime, model files and free space. Nothing downloads until you choose it."

    @Property("QVariantList", notify=changed)
    def artifacts(self):
        return self.rows

    @Property(bool, notify=changed)
    def isBusy(self):
        return self.busy

    @Property(float, notify=changed)
    def progress(self):
        return self.fraction

    @Property(str, notify=changed)
    def statusText(self):
        return self.status

    @Property(str, notify=changed)
    def spaceText(self):
        return (
            f"{self.free_gb:.1f} GB free. Setup requires 12 GB free."
            if self.free_gb
            else "Free space not checked yet."
        )

    @Property(bool, notify=changed)
    def spaceReady(self):
        return self.enough

    def send(self, kind, **fields):
        if (
            self.busy
            or self.host.session.active is not None
            or self.host.voice.isBusy
            or self.host.wake.busy
        ):
            self.status = "Finish current work or use Stop before setup."
            self.changed.emit()
            return
        try:
            if self.worker is None:
                self.worker = Supervisor(self.root, worker_target=setup_worker, owned_job=True)
                self.worker.cancel(self.epoch)
            model_root = self.host.settings.speech_assets_dir or str(default_models())
            accepted = self.worker.submit(
                SetupJob(kind=kind, generation=self.epoch, root=model_root, **fields)
            )
            if not accepted:
                raise RuntimeError()
            self.busy = True
            self.fraction = 0.0
            self.status = (
                "Checking local files…"
                if kind == "inspect"
                else "Working on the selected verified asset. Stop cancels; interrupted downloads can resume."
            )
        except (OSError, ValueError, RuntimeError):
            self.status = "Setup is unavailable. Typed commands still work; check folder permissions and storage."
        self.changed.emit()

    @Slot()
    def inspect(self):
        self.send("inspect")

    @Slot(str, bool)
    def download(self, key, accepted):
        if not accepted or not self.enough:
            self.status = (
                "Review the licenses and check the required free space before downloading."
            )
            self.changed.emit()
            return
        self.send("download", artifact=key)

    @Slot(str)
    def importAsset(self, key):
        path = QFileDialog.getExistingDirectory(
            None, "Choose the local models folder to import from"
        )
        if path:
            self.send("import", source=path, artifact=key)

    @Slot()
    def cancel(self):
        self.epoch += 1
        if self.worker:
            self.worker.cancel(self.epoch)
        self.busy = False
        self.fraction = 0.0
        self.status = (
            "Setup stopped. Verified assets remain usable; owned partial downloads can resume."
        )
        self.changed.emit()

    def poll(self):
        if not self.worker:
            return
        for event in self.worker.poll():
            if "generation" in event and event["generation"] != self.epoch:
                continue
            kind = event["kind"]
            if kind == "setup_progress":
                self.fraction = event["completed"] / max(1, event["total"])
            elif kind == "setup_inventory":
                self.rows = event["rows"]
                self.free_gb = event["free_gb"]
                self.enough = event["setup_space_ok"]
                self.busy = False
                self.fraction = 1.0
                self.status = "Local files checked. Only checksum-verified assets can load."
            elif kind in {"setup_error", "worker_failed"}:
                self.busy = False
                self.status = "Setup interrupted or verification failed. Check storage, permissions and connectivity, then resume or import a verified file. Existing unexpected files are preserved."
            elif kind == "setup_cancelled":
                self.busy = False
            self.changed.emit()

    def shutdown(self):
        self.cancel()
        return self.worker.shutdown() if self.worker else True
