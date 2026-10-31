"""Real Unicode/focus/overlay tests against a freshly spawned disposable app only."""

import json
import subprocess
import sys
import time

import win32gui
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget

from autumn.actions.schemas import Plan, TypeText
from autumn.controller.contracts import Request
from autumn.controller.worker import Job, Supervisor
from autumn.ui.confirmation import ConfirmationOverlay
from autumn.winworker.dictation import Dictation


class OverlayDriver(QObject):
    showApproval = Signal(str, str)
    hideApproval = Signal()

    def confirm(self):
        pass

    def cancelApproval(self):
        pass


def run(report, root):
    app = QApplication.instance() or QApplication([])
    owner = QWidget()
    owner.setWindowTitle("Autumn — disposable verification")
    owner.resize(420,180)
    owner.show()
    owner.activateWindow()
    owner.raise_()
    for _ in range(8):
        app.processEvents()
        time.sleep(.02)
    root.mkdir(parents=True, exist_ok=True)
    ready = root / "target-ready.json"
    if ready.exists():
        ready.unlink()
    command = [sys.executable]
    if not getattr(sys, "frozen", False):
        command += ["-m", "autumn.main"]
    child = subprocess.Popen(
        [*command, "--dictation-fixture-ready", str(ready), "--data-dir", str(root)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    worker = None
    overlay = None
    result = {
        "frozen": bool(getattr(sys, "frozen", False)),
        "scope": "disposable native Edit only; no microphone/speakers/personal targets",
        "checks": {},
    }
    start = time.monotonic()

    def check(name, value):
        result["checks"][name] = bool(value)
        if not value:
            raise AssertionError(name)

    def wait(kind, timeout=12):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            app.processEvents()
            for event in worker.poll():
                if event["kind"] == kind:
                    return event
                if event["kind"] == "worker_failed" and kind != "worker_failed":
                    raise RuntimeError("Worker failed")
            time.sleep(0.01)
        raise TimeoutError(kind)

    try:
        until = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < until:
            app.processEvents()
            time.sleep(0.02)
        info = json.loads(ready.read_text())
        target = Dictation()
        snapshot = target.snapshot(info["window"], info["edit"])
        try:
            target.snapshot(info["window"], info["password"])
            password_refused = False
        except PermissionError:
            password_refused = True
        check("password_control_refused", password_refused)
        driver = OverlayDriver()
        overlay = ConfirmationOverlay(driver)
        win32gui.SetForegroundWindow(info["window"])
        before = win32gui.GetForegroundWindow()
        driver.showApproval.emit("Autumn disposable target", "Public synthetic preview")
        for _ in range(5):
            app.processEvents()
            time.sleep(0.02)
        check(
            "overlay_does_not_activate", win32gui.GetForegroundWindow() == before == info["window"]
        )
        check(
            "overlay_noactivate_style",
            win32gui.GetWindowLong(int(overlay.winId()), -20) & 0x08000000,
        )
        driver.hideApproval.emit()
        worker = Supervisor(root / "worker")
        wait("ready")
        worker.submit(Job(kind="dictation_targets", generation=0))
        rows = wait("dictation_targets")["rows"]
        selected = next(
            r["id"] for r in rows if r["label"].startswith("Autumn disposable dictation target")
        )
        sample = "Autumn café नमस्ते 🙂"
        plan = Plan(steps=(TypeText(arguments={"text": sample, "target_id": selected}),))
        request = Request(generation=0, origin="button")
        worker.submit(Job(kind="execute", generation=0, request=request, plan=plan))
        approval = wait("confirmation")
        win32gui.SetForegroundWindow(info["window"])
        worker.submit(
            Job(kind="confirm", generation=0, confirmation_id=approval["token"], approved=True)
        )
        outcome = wait("action_result")["outcome"]
        until = time.monotonic() + 1
        while win32gui.GetWindowText(info["edit"]) != sample and time.monotonic() < until:
            time.sleep(0.02)
        check("unicode_exact_in_disposable_edit", win32gui.GetWindowText(info["edit"]) == sample)
        check("delivery_honestly_unverified", outcome["status"] == "unverified")
        wait("action_finished") if worker.busy_until else None
        # Reuse cannot cause another insertion.
        worker.submit(
            Job(kind="confirm", generation=0, confirmation_id=approval["token"], approved=True)
        )
        time.sleep(0.1)
        check("replay_does_not_duplicate", win32gui.GetWindowText(info["edit"]) == sample)
        # A fresh pending request is cancelled before any input is dispatched.
        worker.submit(Job(kind="execute", generation=0, request=Request(generation=0), plan=plan))
        wait("confirmation")
        worker.cancel(1)
        wait("action_finished")
        check("cancel_pending_approval_no_input", win32gui.GetWindowText(info["edit"]) == sample)
        # A worker crash loses approvals and payloads instead of replaying them.
        worker.submit(Job(kind="execute", generation=1, request=Request(generation=1), plan=plan))
        wait("confirmation")
        worker.process.terminate()
        wait("worker_failed")
        wait("ready")
        check("restart_no_duplicate_input", win32gui.GetWindowText(info["edit"]) == sample)
        # Steal foreground after one accepted character; next checkpoint must stop.
        win32gui.SetWindowText(info["edit"], "")
        win32gui.SetForegroundWindow(info["window"])
        sent = []
        original = target.send_character

        def stealing(character):
            accepted = original(character)
            sent.append(character)
            win32gui.SetForegroundWindow(info["steal"])
            return accepted

        target.send_character = stealing
        partial = target.type_text(snapshot, "Public focus test", lambda: True)
        check(
            "focus_loss_stops_after_one_character", partial.status == "partial" and len(sent) == 1
        )
        result["passed"] = all(result["checks"].values())
    except Exception as error:
        result["passed"] = False
        result["error_type"] = type(error).__name__
    finally:
        if overlay:
            overlay.hide()
        owner.hide()
        if worker:
            result["worker_clean_shutdown"] = worker.shutdown()
        child.terminate()
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=1)
    result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["passed"] else 1
