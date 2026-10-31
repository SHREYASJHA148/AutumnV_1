"""Review only the isolated Autumn setup surface; no desktop capture or audio."""
import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from autumn.controller.worker import Supervisor
from autumn.storage.settings import Settings, atomic_save
from autumn.ui.desktop import Desktop
from autumn.ui.viewmodel import ViewModel

if __name__ == '__main__':
    os.environ['QT_QUICK_BACKEND']='software'
    os.environ['QT_QUICK_CONTROLS_STYLE']='Fusion'
    root = Path(__file__).resolve().parents[1]
    isolated = root / '.cache/phase7-setup-review'
    atomic_save(isolated/'config/settings.json',Settings(speech_assets_dir=str(isolated/'models')))
    app = QApplication(sys.argv[:1])
    vm = ViewModel(Supervisor(isolated),preview_mode=True)
    desktop = Desktop(vm,app)
    engine = QQmlApplicationEngine()
    for name,value in {'vm':vm,'desktop':desktop,'voice':vm.voice,'advanced':vm.advanced,'wake':vm.wake,'setup':vm.setup}.items():
        engine.rootContext().setContextProperty(name,value)
    engine.load(QUrl.fromLocalFile(str(root/'src/autumn/ui/Main.qml')))
    window = engine.rootObjects()[0]
    assert isinstance(window,QQuickWindow)
    desktop.window = window
    started = time.monotonic()
    requested = [False]
    result = {}
    timer = QTimer()

    def uncaught(kind,error,traceback):
        result.update(passed=False,error_type=kind.__name__)
        timer.stop()
        app.quit()

    sys.excepthook=uncaught

    def tick():
        if time.monotonic()-started>15:
            result.update(passed=False)
            app.quit()
        elif vm.ready and not requested[0]:
            window.setProperty('page',9)
            vm.setup.inspect()
            requested[0]=True
        elif requested[0] and len(vm.setup.rows)==8 and not vm.setup.busy:
            timer.stop()
            window.grabWindow().save(str(root/'.cache/phase7-setup-review.png'))
            result.update(passed=True,rows=len(vm.setup.rows),network_requests=0,audio_hardware_opened=False)
            app.quit()

    timer.timeout.connect(tick)
    timer.start(100)
    app.exec()
    desktop.shutdown()
    result['clean_shutdown']=vm.shutdown()
    (root/'docs/reports/phase7_setup_ui.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.get('passed') else 1)
