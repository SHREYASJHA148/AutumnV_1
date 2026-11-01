"""Real local brain/catalog/tray startup; fake microphone, no desktop actions."""
import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from autumn.controller.worker import Supervisor
from autumn.storage.settings import Settings, atomic_save
from autumn.ui.desktop import Desktop
from autumn.ui.viewmodel import ViewModel


class FakeAudio:
    def __init__(self):
        self.sent=[]
    def send(self,role,kind,**fields):
        self.sent.append((role,kind,fields))
        return True
    def poll(self):
        return []
    def cancel(self):
        pass
    def shutdown(self):
        return True


if __name__=='__main__':
    os.environ['QT_QUICK_BACKEND']='software'
    os.environ['QT_QUICK_CONTROLS_STYLE']='Fusion'
    root=Path(__file__).resolve().parents[1]
    fixture=root/'.cache/personal-startup-probe'
    atomic_save(fixture/'config/settings.json',Settings(start_brain_on_launch=True,broad_open_access=True,hands_free_on_launch=True,speech_assets_dir=str(root/'models')))
    app=QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(root/'src/autumn/ui/Autumn.ico')))
    vm=ViewModel(Supervisor(fixture),launch_services=True)
    vm.voice.service=FakeAudio()
    desktop=Desktop(vm,app)
    engine=QQmlApplicationEngine()
    for name,value in {'vm':vm,'voice':vm.voice,'desktop':desktop,'advanced':vm.advanced,'wake':vm.wake,'setup':vm.setup}.items():
        engine.rootContext().setContextProperty(name,value)
    engine.load(QUrl.fromLocalFile(str(root/'src/autumn/ui/Main.qml')))
    window=engine.rootObjects()[0]
    assert isinstance(window,QQuickWindow)
    desktop.window=window
    window.visibilityChanged.connect(desktop.onMinimized)
    started=time.monotonic()
    minimized=[0.0]
    result={}
    timer=QTimer()

    def fail(kind,error,traceback):
        result.update(passed=False,error_type=kind.__name__)
        app.quit()
    sys.excepthook=fail

    def tick():
        if time.monotonic()-started>50:
            result.update(passed=False,stage=vm.launch_stage,brain_status=vm.model_status)
            app.quit()
        elif vm.launch_stage=='done' and vm.voice.recording and not minimized[0]:
            result.update(brain_ready=vm.model_status.startswith('Local brain ready'),brain_status=vm.model_status,enabled_apps=sum(a.enabled and a.reviewed for a in vm.settings.apps),folders=len(vm.settings.folders),brain_startup_and_discovery_seconds=round(time.monotonic()-started,3),window_icon_present=not app.windowIcon().isNull(),microphone_opened=False,action_dispatches=0)
            window.setProperty('page',0)
            window.grabWindow().save(str(root/'docs/media/autumn-personal.png'))
            window.showMinimized()
            minimized[0]=time.monotonic()
        elif minimized[0] and time.monotonic()-minimized[0]>.3:
            result.update(tray_visible=desktop.tray.isVisible(),minimized_to_tray=not window.isVisible(),hands_free_still_enabled=vm.voice.hands_free,capture_request_still_active=vm.voice.recording)
            result['passed']=all(result[k] for k in ('brain_ready','window_icon_present','tray_visible','minimized_to_tray','hands_free_still_enabled','capture_request_still_active')) and result['enabled_apps']>0
            app.quit()

    timer.timeout.connect(tick)
    timer.start(50)
    app.exec()
    timer.stop()
    desktop.shutdown()
    result['clean_shutdown']=vm.shutdown()
    (root/'docs/reports/personal_startup_probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    raise SystemExit(0 if result.get('passed') and result['clean_shutdown'] else 1)
