"""Self-closing in-app test. Only fixed test input and metadata are used."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QTimer, Slot
from PySide6.QtTest import QTest


class SmokeTrial(QObject):
    def __init__(self, app, window, vm, native, report: Path) -> None:
        super().__init__()
        self.app, self.window, self.vm, self.native, self.report = app, window, vm, native, report
        self.timer = QTimer(self)
        self.timer.setInterval(65)
        self.timer.timeout.connect(self.step)
        self.started = time.monotonic()
        self.index = 0
        self.stage = "startup"
        self.samples: dict[str, list[float]] = {"input": [], "stop": []}
        self.pending: list[tuple[str, float]] = []
        self.measure_start = 0.0
        self.child = None
        self.phase3 = False
        self.focus_target = None
        self.checks: dict[str, bool] = {}
        self.error = False
        self.error_type = None
        self.original_exception_hook = sys.excepthook
        sys.excepthook = self.uncaught
        vm.acknowledged.connect(self.ack)
        window.frameSwapped.connect(self.frame)

    def start(self) -> None:
        self.timer.start()

    def uncaught(self, kind, error, traceback) -> None:
        # Qt slots otherwise print and swallow Python exceptions, creating false-positive UI trials.
        self.error = True
        self.error_type = kind.__name__
        self.timer.stop()
        self.app.quit()

    @Slot(str)
    def ack(self, kind: str) -> None:
        if self.measure_start:
            self.pending.append((kind, self.measure_start))
            self.window.requestUpdate()

    @Slot()
    def frame(self) -> None:
        now = time.monotonic()
        for kind, started in self.pending:
            self.samples[kind].append((now - started) * 1000)
        self.pending.clear()

    def step(self) -> None:
        try:
            self._step()
        except Exception as error:
            # Never persist exception strings (may include paths or user data).
            self.error = True
            self.error_type = type(error).__name__
            self.timer.stop()
            self.app.quit()

    def _step(self) -> None:
        if time.monotonic() - self.started > 30:
            self.checks["finished_before_timeout"] = False
            self.timer.stop()
            self.app.quit()
            return
        if self.stage == "startup":
            if not self.vm.canSend:
                return
            if not self.vm.preview_mode and self.vm.settings.model_enabled:
                self.vm.setModelOptions(False,False)
                self.stage="disable_model_for_load"
                return
            self.input = self.window.findChild(QObject, "commandInput")
            self.stop_button = self.window.findChild(QObject, "stopButton")
            self.checks["voice_setup_loaded"] = self.window.findChild(QObject, "transcriptEditor") is not None
            self.checks["talk_control_loaded"] = self.window.findChild(QObject, "talkButton") is not None
            self.checks["dictation_controls_loaded"] = self.window.findChild(QObject, "dictationTarget") is not None
            self.checks["routine_editor_loaded"] = self.window.findChild(QObject, "routineName") is not None
            self.checks["wake_setup_loaded"] = self.window.findChild(QObject, "wakeCheckButton") is not None
            self.checks["wake_disabled_at_launch"] = not self.vm.wake.enabled and not self.vm.wake.monitoring
            screen=self.window.screen().availableGeometry()
            self.checks["window_fits_available_screen"] = self.window.width()<=screen.width() and self.window.height()<=screen.height()
            self.window.setProperty("page", 0)
            self.checks.update(qml_loaded=True, microphone_disabled=not self.vm.voiceReady,
                               input_available=self.input is not None,
                               session_notifications=self.native.session_registered,
                               shortcuts_registered=len(self.native.registered)+bool(self.native.hook.handle) == len(self.native.callbacks))
            self.launch_ms = (time.monotonic() - self.started) * 1000
            # Fill the one-running/five-pending request queue while the worker is busy.
            for _ in range(6):
                self.vm.submit("help")
            self.vm.submit("help")
            self.checks["bounded_request_queue"] = self.vm.queuedCount == 5 and "Busy:" in self.vm.notice
            self.vm.stop()
            self.vm.toggleVoice()
            self.vm.stop()
            self.checks["stop_returns_ptt_ready"] = self.vm.voiceReady
            self.vm.toggleVoice()
            self.vm.suspend()
            self.vm.submit("Must be blocked while suspended")
            self.checks["suspend_blocks_requests"] = self.vm.session.active is None
            self.vm.resume()
            self.checks["resume_microphone_disabled"] = not self.vm.voiceReady
            self.stage = "new_pages"
            self.pages_remaining = [(6,"dictationTarget"),(7,"routineName"),(8,"wakeCheckButton"),(9,"setupCheckButton")]
            self.page_control = None
        elif self.stage == "disable_model_for_load" and not self.vm.settings_pending:
            self.stage="startup"
        elif self.stage == "new_pages":
            if self.page_control:
                item=self.window.findChild(QObject,self.page_control)
                position=item.mapToItem(self.window.contentItem(),QPointF(0,0))
                self.checks[self.page_control+"_visible_in_layout"] = (position.x()>=0 and position.y()>=0 and
                    position.x()+item.width()<=self.window.width()+1 and position.y()+item.height()<=self.window.height()+1)
            if self.pages_remaining:
                page,self.page_control=self.pages_remaining.pop(0)
                self.window.setProperty('page',page)
            else:
                self.window.setProperty('page',0)
                self.stage='load'
        elif self.stage == "load":
            self.measure_start = time.monotonic()
            if self.index % 2 == 0:
                self.input.forceActiveFocus()
                QTest.keyClick(self.window, Qt.Key_A)
                QTest.keyClick(self.window, Qt.Key_Return)
            else:
                p = self.stop_button.mapToScene(QPointF(self.stop_button.width() / 2, self.stop_button.height() / 2))
                QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, QPoint(int(p.x()), int(p.y())))
            self.measure_start = 0.0
            self.index += 1
            if self.index == 80:
                self.stage = "drain"
                self.drain_until = time.monotonic() + 0.8
        elif self.stage == "drain" and time.monotonic() >= self.drain_until:
            self.checks["stop_discards_pending"] = self.vm.session.active is None and not self.vm.session.pending
            self.checks["input_rendered_samples"] = len(self.samples["input"]) == 40
            self.checks["stop_rendered_samples"] = len(self.samples["stop"]) == 40
            self.vm.submit("Fixed completion preview" if self.vm.preview_mode else "help")
            self.stage = "completion"
        elif self.stage == "completion" and self.vm.session.active is None:
            self.checks["command_completed"] = any(row["code"] == ("SIMULATED" if self.vm.preview_mode else "OK") for row in self.vm.history)
            if not self.checks["command_completed"]:
                return
            self.checks["history_has_no_text"] = all(set(row) <= {"created", "skill_id", "origin", "status", "code", "duration_ms"} for row in self.vm.history)
            if not self.vm.preview_mode:
                from autumn.actions.catalog import FolderEntry
                files = self.vm.supervisor.root / "disposable search files"
                files.mkdir(exist_ok=True)
                (files / "gate-check.xlsx").write_bytes(b"Fixed disposable filename fixture")
                self.vm.update_settings(folders=[FolderEntry(id="gate", name="Gate files", path=str(files)).model_dump()])
                self.stage = "search_settings"
                return
            self.vm.clearHistory()
            self.stage = "clear"
        elif self.stage == "search_settings" and not self.vm.settings_pending:
            self.vm.submit("find spreadsheet gate-check in gate files")
            self.stage = "search_complete"
        elif self.stage == "search_complete" and self.vm.session.active is None:
            self.checks["real_filename_search_worker"] = len(self.vm.result_cards) == 1 and self.vm.result_cards[0]["name"] == "gate-check.xlsx"
            if self.phase3:
                self.vm.setModelOptions(True,False)
                self.stage="model_settings"
                return
            self.vm.clearHistory()
            self.stage = "clear"
        elif self.stage=="model_settings" and not self.vm.settings_pending:
            self.vm.submit("Tell me which actions you can perform.")
            self.stage="model_complete"
        elif self.stage=="model_complete" and self.vm.session.active is None:
            self.checks["pinned_model_reply_validated"]=self.vm.model_metrics.get("thinking_disabled",False) and "error" not in self.vm.model_metrics
            self.checks["model_answer_registry_rendered"]=any(m["role"]=="Autumn" and m["text"].startswith("I can:") for m in self.vm.conversation[-2:])
            self.vm.clearHistory()
            self.stage="clear"
        elif self.stage == "clear" and not self.vm.history:
            self.checks["history_cleared"] = True
            self.snapshot_page = 0
            self.stage = "snapshots"
        elif self.stage == "snapshots":
            self.window.grabWindow().save(str(self.vm.supervisor.root / f"page-{self.snapshot_page}.png"))
            self.snapshot_page += 1
            if self.snapshot_page < 5:
                self.window.setProperty("page", self.snapshot_page)
                return
            self.window.setProperty("page", 0)
            from PySide6.QtGui import QWindow

            self.window.grabWindow().save(str(self.vm.supervisor.root / "preview.png"))
            self.focus_target = QWindow()
            self.focus_target.setTitle("Autumn disposable focus target")
            self.focus_target.resize(320, 160)
            self.focus_target.show()
            self.focus_target.requestActivate()
            self.focus_deadline = time.monotonic() + 2
            self.stage = "focus_target"
        elif self.stage == "focus_target":
            if not self.focus_target.isActive() and time.monotonic() < self.focus_deadline:
                return
            self.checks["separate_target_had_focus"] = self.focus_target.isActive() and not self.window.isActive()
            executable = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, "-m", "autumn.main"]
            self.child = subprocess.Popen([*executable, "--data-dir", str(self.vm.supervisor.root)],
                                          creationflags=subprocess.CREATE_NO_WINDOW)
            self.stage = "second_instance"
            self.focus_deadline = time.monotonic() + 3
        elif self.stage == "second_instance" and self.child.poll() is not None:
            if not self.window.isActive() and time.monotonic() < self.focus_deadline:
                return
            self.checks["second_instance_exit_zero"] = self.child.returncode == 0
            self.checks["first_instance_alive"] = self.window.isVisible() and self.vm.canSend
            self.checks["second_instance_focused_window"] = self.window.isActive()
            self.checks["finished_before_timeout"] = True
            self.focus_target.close()
            self.timer.stop()
            self.app.quit()

    def finish(self, shutdown_clean: bool) -> int:
        sys.excepthook = self.original_exception_hook
        if self.child is not None and self.child.poll() is None:
            self.child.terminate()
            self.child.wait(timeout=2)
        self.checks["workers_closed"] = shutdown_clean
        self.checks["no_test_exception"] = not self.error
        self.checks["no_qt_warnings"] = not getattr(self, "qt_issues", [])
        timings = {}
        for kind, values in self.samples.items():
            values = sorted(values)
            p95 = values[max(0, math.ceil(len(values) * 0.95) - 1)] if values else None
            timings[kind] = {"samples": len(values), "p95_ms": round(p95, 3) if p95 is not None else None}
            self.checks[f"{kind}_p95_below_200ms"] = p95 is not None and p95 <= 200
        self.report.parent.mkdir(parents=True, exist_ok=True)
        passed = bool(self.checks) and all(self.checks.values())
        self.report.write_text(json.dumps({"passed": passed, "frozen": bool(getattr(sys, "frozen", False)),
            "checks": self.checks, "test_exception_type": self.error_type, "input_to_render": timings,
            "load": "80 alternating typed-input/Stop events, 100-row conversation cap, six-request overflow trial; worker active",
            "ui_ready_after_qml_ms": round(getattr(self, "launch_ms", 0), 3),
            "elapsed_seconds": round(time.monotonic() - self.started, 3)}, indent=2), encoding="utf-8")
        return 0 if passed else 1
