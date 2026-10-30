"""Explicit owner-operated hook/confirmation/Stop fixture; stores only chord counts."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import time
from PySide6.QtCore import QAbstractNativeEventFilter,Qt,QTimer
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLabel,QPushButton

ROOT=Path(__file__).resolve().parents[1]
user=ctypes.WinDLL('user32',use_last_error=True)
user.GetForegroundWindow.restype=ctypes.c_void_p
user.SetWindowsHookExW.restype=ctypes.c_void_p
user.CallNextHookEx.restype=ctypes.c_ssize_t
CALLBACK=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,ctypes.c_size_t,ctypes.c_void_p)
user.SetWindowsHookExW.argtypes=[ctypes.c_int,CALLBACK,ctypes.c_void_p,wintypes.DWORD]
user.CallNextHookEx.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_size_t,ctypes.c_void_p]

class Filter(QAbstractNativeEventFilter):
    def __init__(self,owner): super().__init__(); self.owner=owner
    def nativeEventFilter(self,kind,message):
        msg=wintypes.MSG.from_address(int(message))
        if msg.message==0x312:
            if msg.wParam==701:
                self.owner.data['confirm_events']+=1
                self.owner.data['confirm_preserved_target']=bool(self.owner.target) and user.GetForegroundWindow()==self.owner.target
                self.owner.label.setText('Confirm received. Now hold/release Ctrl+Alt+Space, then press Ctrl+Alt+F12.')
            if msg.wParam==702:
                self.owner.data['stop_events']+=1
                self.owner.label.setText('Stop received without speech or a model. Close this fixture when finished.')
                self.owner.overlay.hide()
            self.owner.save(); return True,0
        return False,0

class Fixture(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Autumn keyboard and confirmation test'); self.resize(670,230)
        self.data={'hold_down':0,'hold_up':0,'confirm_events':0,'stop_events':0,'confirm_preserved_target':False,
            'typed_keys_saved':False,'elevated_window_tested':False,'capture_stop_tested':False}
        self.target=None; self.held=False
        self.overlay=QLabel('Autumn confirmation overlay — press Ctrl+Alt+F11',None,
            Qt.Tool|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus)
        self.overlay.setAttribute(Qt.WA_ShowWithoutActivating)
        layout=QVBoxLayout(self)
        self.label=QLabel('1. Click Arm.\n2. Switch to Autumn disposable target and click its empty field.\n3. Wait for overlay, press Ctrl+Alt+F11.\n4. Hold/release Ctrl+Alt+Space; press Ctrl+Alt+F12.'); layout.addWidget(self.label)
        button=QPushButton('Arm overlay after five seconds'); button.clicked.connect(self.arm); layout.addWidget(button)
        self.filter=Filter(self); QApplication.instance().installNativeEventFilter(self.filter)
        self.data['confirm_registered']=bool(user.RegisterHotKey(None,701,0x4003,0x7A))
        self.data['stop_registered']=bool(user.RegisterHotKey(None,702,0x4003,0x7B))
        @CALLBACK
        def hook(code,wparam,lparam):
            if code>=0:
                vk=ctypes.cast(lparam,ctypes.POINTER(wintypes.DWORD)).contents.value
                if vk==0x20:
                    if wparam in (0x100,0x104) and user.GetAsyncKeyState(0x11)&0x8000 and user.GetAsyncKeyState(0x12)&0x8000 and not self.held:
                        self.held=True; self.data['hold_down']+=1; self.save()
                    if wparam in (0x101,0x105) and self.held:
                        self.held=False; self.data['hold_up']+=1; self.save()
            return user.CallNextHookEx(None,code,wparam,lparam)
        self.callback=hook
        self.handle=user.SetWindowsHookExW(13,self.callback,None,0)
        self.data['hook_installed']=bool(self.handle); self.save()
        QTimer.singleShot(600000,self.close)
    def arm(self):
        self.label.setText('Switch to Autumn disposable target and click its empty field now. Overlay appears in five seconds.')
        def show():
            user.FindWindowW.restype=ctypes.c_void_p
            expected=user.FindWindowW(None,'Autumn disposable target')
            self.target=expected if expected and user.GetForegroundWindow()==expected else None
            self.data['target_focused_before_overlay']=bool(self.target)
            self.overlay.show(); self.save()
        QTimer.singleShot(5000,show)
    def save(self):
        (ROOT/'docs/reports/keyboard_probe.json').write_text(json.dumps(self.data,indent=2),encoding='utf-8')
    def closeEvent(self,event):
        if self.handle:
            user.UnhookWindowsHookEx.argtypes=[ctypes.c_void_p]; user.UnhookWindowsHookEx(self.handle)
        user.UnregisterHotKey(None,701); user.UnregisterHotKey(None,702)
        self.overlay.close(); self.data['hook_removed']=True; self.save(); event.accept()

if __name__=='__main__':
    app=QApplication([]); fixture=Fixture(); fixture.show(); app.exec()
