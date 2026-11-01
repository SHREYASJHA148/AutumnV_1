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
    parser.add_argument("--phase5-probe-report",type=Path,help="Disposable native dictation/overlay test")
    parser.add_argument("--dictation-fixture-ready",type=Path,help="Spawn the disposable diagnostic Edit target")
    parser.add_argument("--wake-probe-report",type=Path,help="Synthetic ONNX wake test; never opens microphone")
    parser.add_argument('--ui-preview-report',type=Path,help='Render a public demonstration of the UI in isolation')
    parser.add_argument('--ui-preview-image',type=Path,help='Image of only the isolated Autumn window')
    parser.add_argument('--soak-report',type=Path,help='Isolated real-time software stability trial; no audio hardware')
    parser.add_argument('--soak-seconds',type=int,default=7200)
    parser.add_argument('--login',action='store_true',help='Login startup keeps the microphone off')
    args = parser.parse_args()
    if args.soak_report and (args.data_dir is None or not 30 <= args.soak_seconds <= 86400):
        parser.error('Software soak requires isolated --data-dir and 30–86400 seconds')
    if args.soak_report and (args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report or args.ui_preview_report):
        parser.error('Run each diagnostic separately')
    if args.ui_preview_report and (args.data_dir is None or args.ui_preview_image is None):
        parser.error('UI preview requires isolated --data-dir and --ui-preview-image')
    if args.wake_probe_report:
        from autumn.diagnostics.wake_probe import run
        return run(args.wake_probe_report)
    if args.phase5_probe_report or args.dictation_fixture_ready:
        if args.data_dir is None:
            parser.error("An isolated --data-dir is required")
        if args.dictation_fixture_ready:
            from autumn.diagnostics.dictation_target import run
            return run(args.dictation_fixture_ready)
        from autumn.diagnostics.phase5_probe import run
        return run(args.phase5_probe_report,args.data_dir.resolve())
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
    from PySide6.QtGui import QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtWidgets import QApplication, QMessageBox

    from autumn.controller.worker import Supervisor
    from autumn.storage.settings import app_directory
    from autumn.ui.viewmodel import ViewModel
    from autumn.ui.windows import NativeEvents, SingleInstance

    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    qt_issues = []
    if args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report or args.ui_preview_report or args.soak_report:
        def qt_message(kind, context, message):
            if kind in {QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg}:
                qt_issues.append(int(kind.value))
        qInstallMessageHandler(qt_message)
    app.setApplicationName("Autumn")
    app.setOrganizationName("Autumn Local")
    app.setApplicationVersion("0.7.1")
    app.setWindowIcon(QIcon(str(Path(__file__).parent/'ui/Autumn.ico')))
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
    supervisor = Supervisor(root, allow_faults=bool(args.soak_report))
    vm = ViewModel(supervisor, preview_mode=bool(args.smoke_report or args.ui_preview_report),launch_services=args.data_dir is None,launch_listening=not args.login)
    from autumn.ui.desktop import Desktop
    desktop = Desktop(vm,app)
    from autumn.ui.confirmation import ConfirmationOverlay
    overlay = ConfirmationOverlay(vm.advanced)
    native = NativeEvents(vm.stop, vm.voice.toggleRecording, vm.suspend, vm.resume,
                         on_hold_start=vm.voice.beginHold,on_hold_end=vm.voice.endHold,
                         on_confirm=vm.advanced.confirm,on_cancel=vm.advanced.cancelApproval)
    app.installNativeEventFilter(native)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("vm", vm)
    engine.rootContext().setContextProperty('voice',vm.voice)
    engine.rootContext().setContextProperty('advanced',vm.advanced)
    engine.rootContext().setContextProperty('wake',vm.wake)
    engine.rootContext().setContextProperty('desktop',desktop)
    engine.rootContext().setContextProperty('setup',vm.setup)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "ui/Main.qml")))
    if not engine.rootObjects():
        failure_report = args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report or args.ui_preview_report or args.soak_report
        if failure_report:
            import json
            failure_report.parent.mkdir(parents=True,exist_ok=True)
            failure_report.write_text(json.dumps({"passed":False,"stage":"qml_load","qt_warning_count":len(qt_issues)}),encoding="utf-8")
        vm.shutdown()
        native.close()
        instance.close()
        return 1
    window = engine.rootObjects()[0]
    desktop.window = window
    window.visibilityChanged.connect(desktop.onMinimized)
    if not isinstance(window, QQuickWindow):
        vm.shutdown()
        native.close()
        instance.close()
        return 1
    instance.publish(int(window.winId()))
    native.bind_window(int(window.winId()))

    def shortcuts() -> None:
        if args.soak_report:
            return
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
            if vm.launch_services:
                vm.checkLocalBrain()

    focus_timer.timeout.connect(focus_existing)
    focus_timer.start()
    clean = []

    def shutdown() -> None:
        desktop.shutdown()
        overlay.hide()
        focus_timer.stop()
        native.close()
        clean.append(vm.shutdown())
        instance.close()

    app.aboutToQuit.connect(shutdown)
    _preview = None
    if args.ui_preview_report:
        from autumn.diagnostics.preview import Preview
        _preview = Preview(app,window,vm,args.ui_preview_report,args.ui_preview_image)
    _soak = None
    if args.soak_report:
        from autumn.diagnostics.soak import Soak
        _soak = Soak(app,window,vm,args.soak_report,args.soak_seconds)
    smoke = None
    if args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report:
        from autumn.diagnostics.smoke import SmokeTrial
        smoke = SmokeTrial(app, window, vm, native, args.smoke_report or args.phase2_smoke_report or args.phase3_smoke_report)
        smoke.phase3 = bool(args.phase3_smoke_report)
        smoke.qt_issues = qt_issues
        smoke.start()
    result = app.exec()
    if args.soak_report or args.ui_preview_report:
        import json
        report = args.soak_report or args.ui_preview_report
        if report.exists():
            details = json.loads(report.read_text(encoding='utf-8'))
            details.update(clean_shutdown=bool(clean and clean[0]),qt_warning_count=len(qt_issues))
            report.write_text(json.dumps(details,indent=2),encoding='utf-8')
    if smoke is not None:
        return smoke.finish(bool(clean and clean[0]))
    return result if clean and clean[0] else 1


if __name__ == "__main__":
    raise SystemExit(main())
