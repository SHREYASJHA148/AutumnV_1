"""Desktop entry point. Live capture stays off; planning uses pinned loopback inference."""
from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from pathlib import Path


def main() -> int:
    # Required before importing Qt or constructing anything in a frozen child.
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description="Autumn local desktop assistant")
    parser.add_argument("--data-dir", type=Path, help="Explicit isolated settings directory for testing")
    parser.add_argument("--smoke-report", type=Path, help="Run a self-closing, metadata-only build test")
    parser.add_argument("--phase2-smoke-report", type=Path, help="Self-closing typed-action UI test using only capabilities help")
    parser.add_argument("--phase3-smoke-report", type=Path, help="Self-closing UI and pinned-model capabilities test")
    parser.add_argument("--speech-probe-report", type=Path, help="Synthetic in-memory speech test; no microphone or playback")
    args = parser.parse_args()
    if (args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report or args.speech_probe_report) and args.data_dir is None:
        parser.error("Smoke trials require an explicit isolated --data-dir")
    if args.speech_probe_report:
        try:
            from autumn.diagnostics.speech_probe import run
            return run(args.speech_probe_report, args.data_dir.resolve())
        except Exception as error:
            import json
            import traceback
            frames = traceback.extract_tb(error.__traceback__)
            details = {"pipeline_operational": False, "stage": "probe_initialization", "error_type": type(error).__name__,
                       "frames": [{"module": Path(frame.filename).name, "line": frame.lineno} for frame in frames],
                       "missing_module": error.name if isinstance(error, ModuleNotFoundError) else None}
            args.speech_probe_report.parent.mkdir(parents=True, exist_ok=True)
            args.speech_probe_report.write_text(json.dumps(details, indent=2), encoding="utf-8")
            return 1
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")

    from PySide6.QtCore import QTimer, QtMsgType, QUrl, qInstallMessageHandler
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtWidgets import QApplication, QMessageBox

    from autumn.controller.worker import Supervisor
    from autumn.storage.settings import app_directory
    from autumn.ui.viewmodel import ViewModel
    from autumn.ui.windows import NativeEvents, SingleInstance

    app = QApplication(sys.argv[:1])
    qt_issues = []
    if args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report:
        def qt_message(kind, context, message):
            if kind in {QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg}:
                qt_issues.append(int(kind.value))
        qInstallMessageHandler(qt_message)
    app.setApplicationName("Autumn")
    app.setOrganizationName("Autumn Local")
    app.setApplicationVersion("0.4.0")
    root = args.data_dir.resolve() if args.data_dir else app_directory()
    try:
        instance = SingleInstance(root)
    except OSError:
        QMessageBox.critical(None, "Autumn", "Could not start the single-instance guard. No microphone or actions were started.")
        return 1
    if not instance.primary:
        instance.request_focus()
        instance.close()
        return 0
    supervisor = Supervisor(root)
    vm = ViewModel(supervisor, preview_mode=bool(args.smoke_report))
    native = NativeEvents(vm.stop, vm.voice.toggleRecording, vm.suspend, vm.resume,
                         on_hold_start=vm.voice.beginHold,on_hold_end=vm.voice.endHold)
    app.installNativeEventFilter(native)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("vm", vm)
    engine.rootContext().setContextProperty('voice',vm.voice)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "ui/Main.qml")))
    if not engine.rootObjects():
        failure_report = args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report
        if failure_report:
            import json
            failure_report.parent.mkdir(parents=True,exist_ok=True)
            failure_report.write_text(json.dumps({"passed":False,"stage":"qml_load","qt_warning_count":len(qt_issues)}),encoding="utf-8")
        vm.shutdown()
        native.close()
        instance.close()
        return 1
    window = engine.rootObjects()[0]
    if not isinstance(window, QQuickWindow):
        vm.shutdown()
        native.close()
        instance.close()
        return 1
    instance.publish(int(window.winId()))
    native.bind_window(int(window.winId()))

    def shortcuts() -> None:
        vm.shortcut_rows = native.register(vm.settings.hotkeys,vm.settings.capture_mode)
        vm.shortcut_rows.append({"name": "Session notifications", "detail": "Registered" if native.session_registered else "Unavailable; close the app before lock or sleep"})
        vm.changed.emit()

    vm.shortcutsChanged.connect(shortcuts)
    focus_timer = QTimer(app)
    focus_timer.setInterval(50)

    def focus_existing() -> None:
        if instance.focus_requested():
            window.showNormal()
            window.raise_()
            window.requestActivate()

    focus_timer.timeout.connect(focus_existing)
    focus_timer.start()
    clean = []

    def shutdown() -> None:
        focus_timer.stop()
        native.close()
        clean.append(vm.shutdown())
        instance.close()

    app.aboutToQuit.connect(shutdown)
    smoke = None
    if args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report:
        from autumn.diagnostics.smoke import SmokeTrial
        smoke = SmokeTrial(app, window, vm, native, args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report)
        smoke.phase3 = bool(args.phase3_smoke_report)
        smoke.qt_issues = qt_issues
        smoke.start()
    result = app.exec()
    if smoke is not None:
        return smoke.finish(bool(clean and clean[0]))
    return result if clean and clean[0] else 1


if __name__ == "__main__":
    raise SystemExit(main())
