"""Self-closing Qt/QML/tray and non-activating-overlay spike, not product UI."""
from __future__ import annotations

import ctypes
import json
from pathlib import Path
import sys
import faulthandler
import os

faulthandler.dump_traceback_later(20)

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QSystemTrayIcon

ROOT = Path(os.environ.get('AUTUMN_PROBE_ROOT', str(Path(__file__).resolve().parents[1])))


def run() -> int:
    print('Qt probe: creating QApplication', flush=True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    engine = QQmlApplicationEngine()
    print('Qt probe: loading QML', flush=True)
    qml = '''import QtQuick
import QtQuick.Controls
ApplicationWindow {
    visible: true; width: 500; height: 260; title: "Autumn - Phase 0 test"
    color: "#151b26"
    Label { anchors.centerIn: parent; text: "Autumn: UI compatibility test"; color: "#85baff" }
}'''
    qml_path = ROOT / '.cache' / 'phase0-local.qml'
    qml_path.write_text(qml, encoding='utf-8')
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    print('Qt probe: QML loaded', flush=True)
    pixmap = QPixmap(24, 24)
    pixmap.fill(QColor('#85baff'))
    tray = QSystemTrayIcon(QIcon(pixmap), app)
    tray.setToolTip('Autumn - temporary Phase 0 test')
    tray.show()
    fixture = QLineEdit('Disposable focus target; no input recorded')
    fixture.setWindowTitle('Autumn disposable test target')
    fixture.resize(440, 50)
    overlay = QLabel('Autumn confirmation test — no keyboard focus')
    overlay.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
    overlay.setAttribute(Qt.WA_ShowWithoutActivating)
    report = {'qml_loaded': True, 'tray_available': QSystemTrayIcon.isSystemTrayAvailable()}
    user32 = ctypes.WinDLL('user32')
    user32.GetForegroundWindow.restype = ctypes.c_void_p

    def show_fixture():
        fixture.show()
        fixture.activateWindow()
        fixture.setFocus()

    def show_overlay():
        report['fixture_has_foreground'] = user32.GetForegroundWindow() == int(fixture.winId())
        report['before'] = user32.GetForegroundWindow()
        overlay.show()

    def finish():
        report['overlay_preserves_foreground'] = report['before'] == user32.GetForegroundWindow()
        report.pop('before')
        (ROOT / 'docs/reports/qt_smoke.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
        faulthandler.cancel_dump_traceback_later()
        tray.hide()
        app.quit()

    QTimer.singleShot(500, show_fixture)
    QTimer.singleShot(1200, show_overlay)
    QTimer.singleShot(2000, finish)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(run())
