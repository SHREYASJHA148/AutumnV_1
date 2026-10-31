"""Standalone per-user installer/maintenance UI. Installation requires a button click."""

import argparse
import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from autumn.setup.install import install, sha256, uninstall


class Task(QThread):
    progress = Signal(int)
    finishedResult = Signal(dict)

    def __init__(self, args, payload, metadata):
        super().__init__()
        self.args, self.payload, self.metadata = args, payload, metadata

    def run(self):
        try:
            if self.args.uninstall:
                result = uninstall(self.args.root, registry=not self.args.no_registry)
            else:
                if sha256(self.payload) != self.metadata["payload_sha256"]:
                    raise ValueError("Payload verification failed")
                result = install(
                    self.payload,
                    self.args.root,
                    lambda n, total: self.progress.emit(round(n / total * 100)),
                    maintenance=Path(sys.executable)
                    if getattr(sys, "frozen", False) and not self.args.no_registry
                    else None,
                    registry=not self.args.no_registry,
                )
            self.finishedResult.emit({"passed": True, **result})
        except Exception as error:
            self.finishedResult.emit({"passed": False, "error_type": type(error).__name__})


def main():
    parser = argparse.ArgumentParser(description="Autumn per-user engineering-preview setup")
    parser.add_argument("--root", type=Path, default=Path(os.environ["LOCALAPPDATA"]) / "Autumn")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument(
        "--no-registry", action="store_true", help="Isolated installer validation only"
    )
    parser.add_argument(
        "--smoke-report", type=Path, help="Explicit isolated install/uninstall validation"
    )
    args = parser.parse_args()
    if args.smoke_report and not args.no_registry:
        parser.error("Smoke validation requires --no-registry")
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    payload = base / "payload.zip"
    metadata = json.loads((base / "installer-metadata.json").read_text(encoding="utf-8"))
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Autumn Setup")
    window = QWidget()
    window.setWindowTitle("Autumn — preview setup")
    window.resize(560, 410)
    window.setStyleSheet(
        "QWidget {background:#091323;color:#dceaff;font-family:Segoe UI;font-size:14px} QPushButton {background:#16374b;border:1px solid #4b9cbb;border-radius:9px;padding:12px} QPushButton:disabled {color:#65788c;border-color:#27384b} QProgressBar {border:1px solid #28435d;border-radius:6px;text-align:center} QProgressBar::chunk {background:#52cddd}"
    )
    layout = QVBoxLayout(window)
    layout.setContentsMargins(26, 26, 26, 26)
    layout.setSpacing(16)
    title = QLabel("AUTUMN  /  " + metadata["version"] + " PREVIEW")
    title.setStyleSheet("font-size:23px;color:#74deeb")
    layout.addWidget(title)
    info = QLabel(
        "Remove the application while keeping your settings, history, models and maintenance utility."
        if args.uninstall
        else "Install for this Windows user. No administrator access, model downloads, microphone activation or login startup is enabled by setup.\n\nThis is an engineering preview with acceptance checks still pending."
    )
    info.setWordWrap(True)
    layout.addWidget(info)
    location = QLabel("Location: " + str(args.root))
    location.setWordWrap(True)
    location.setTextInteractionFlags(
        __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.TextSelectableByMouse
    )
    layout.addWidget(location)
    consent = QCheckBox("I reviewed the preview limitations and bundled license notices.")
    layout.addWidget(consent)
    notices = QPushButton('Read bundled notices')
    layout.addWidget(notices)

    def show_notices():
        dialog = QDialog(window)
        dialog.setWindowTitle('Autumn — third-party notices')
        dialog.resize(720, 560)
        notice_layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText((base / 'THIRD_PARTY_NOTICES.md').read_text(encoding='utf-8'))
        notice_layout.addWidget(text)
        dialog.exec()

    notices.clicked.connect(show_notices)
    progress = QProgressBar()
    layout.addWidget(progress)
    status = QLabel("Ready. Close Autumn before maintenance.")
    status.setWordWrap(True)
    layout.addWidget(status)
    action = QPushButton("Remove application" if args.uninstall else "Install for me")
    action.setEnabled(False)
    layout.addWidget(action)
    consent.toggled.connect(action.setEnabled)
    close = QPushButton("Close")
    layout.addWidget(close)
    close.clicked.connect(app.quit)
    task = Task(args, payload, metadata)
    task.progress.connect(progress.setValue)
    result_box = []
    launch = QPushButton('Open Autumn')
    launch.setVisible(False)
    layout.addWidget(launch)

    def open_autumn():
        import subprocess
        subprocess.Popen([str(args.root / 'application' / 'Autumn.exe')], creationflags=subprocess.CREATE_NO_WINDOW)
        app.quit()

    launch.clicked.connect(open_autumn)

    def complete(result):
        result_box.append(result)
        launch.setVisible(result['passed'] and not args.uninstall and not args.smoke_report)
        close.setEnabled(True)
        status.setText(
            (
                "Application removed. Your data and maintenance utility were kept."
                if args.uninstall
                else "Installed. Open application/Autumn.exe to begin local setup."
            )
            if result["passed"]
            else "Maintenance did not finish. Close Autumn and check free space/permissions or the package checksum, then try again. Existing data was not erased."
        )
        if args.smoke_report:
            args.smoke_report.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_report.write_text(json.dumps(result, indent=2), encoding="utf-8")
            app.quit()

    task.finishedResult.connect(complete)

    def begin():
        action.setEnabled(False)
        consent.setEnabled(False)
        close.setEnabled(False)
        status.setText("Working locally. Model files and personal data stay in place.")
        task.start()

    action.clicked.connect(begin)
    # Prevent closing the installer while its transactional file operation is running.
    original_close = window.closeEvent

    def closing(event):
        if task.isRunning():
            event.ignore()
        else:
            original_close(event)

    window.closeEvent = closing
    if args.smoke_report:
        begin()
    else:
        window.show()
    code = app.exec()
    task.wait(1000)
    return (0 if result_box and result_box[-1]["passed"] else 1) if args.smoke_report else code


if __name__ == "__main__":
    raise SystemExit(main())
