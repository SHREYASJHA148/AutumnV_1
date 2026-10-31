"""Open a fresh blank Calculator only when none is running, then close that owned instance."""
import ctypes
import json
import time
from ctypes import wintypes
from pathlib import Path

import comtypes
import psutil

from autumn.actions.catalog import AppEntry
from autumn.actions.engine import Engine
from autumn.actions.schemas import AppArgs, OpenApp, Plan
from autumn.controller.contracts import Request
from autumn.storage.settings import Settings
from autumn.winworker.windows import WindowsAdapter, visible_windows


def run():
    root = Path(__file__).resolve().parents[1]
    report = {"owner_existing_instance_touched": False}
    if any("calculator" in (p.info["name"] or "").casefold() for p in psutil.process_iter(["name"])):
        report.update(status="not tested", reason="Existing Calculator instance left untouched")
    else:
        before_pids = set(psutil.pids())
        before_windows = visible_windows()
        comtypes.CoInitialize()
        try:
            entry = AppEntry(id="calculator", name="Disposable Calculator", kind="package",
                target="Microsoft.WindowsCalculator_8wekyb3d8bbwe!App", enabled=True, reviewed=True)
            engine = Engine(WindowsAdapter(data_dir=root / ".cache/phase2 package probe"), Settings(apps=(entry,)))
            outcome = engine.execute(Plan(steps=(OpenApp(arguments=AppArgs(app_id="calculator")),)),
                Request(generation=0), lambda: True, lambda *_: None)[0]
            report.update(status=outcome.status, code=outcome.code, verification=outcome.verification,
                          passed=outcome.status in {"succeeded", "unverified"})
            until = time.monotonic() + 3
            created = []
            while time.monotonic() < until:
                created = [p for p in psutil.process_iter(["pid", "name"]) if p.pid not in before_pids and "calculator" in (p.info["name"] or "").casefold()]
                if created:
                    break
                time.sleep(0.05)
            user = ctypes.WinDLL("user32")
            user.PostMessageW.argtypes = [wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
            for process in created:
                for hwnd, pid in visible_windows().items():
                    if hwnd not in before_windows and pid == process.pid:
                        user.PostMessageW(hwnd, 0x0010, 0, 0)
                try:
                    process.wait(timeout=2)
                except psutil.TimeoutExpired:
                    # Only the newly created Calculator process identified above is owned by this trial.
                    process.terminate()
                    process.wait(timeout=2)
        finally:
            comtypes.CoUninitialize()
    (root / "docs/reports/phase2_packaged_app.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    run()
