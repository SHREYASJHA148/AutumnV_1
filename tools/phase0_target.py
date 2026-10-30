"""Disposable single-instance edit target; no entered text is read or saved."""
import ctypes
import json
from pathlib import Path
import sys
from ctypes import wintypes
from PySide6.QtWidgets import QApplication,QLineEdit,QVBoxLayout,QWidget,QLabel

ROOT=Path(__file__).resolve().parents[1]
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.CreateMutexW.restype=ctypes.c_void_p
kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
mutex=kernel.CreateMutexW(None,False,'Local\\AutumnPhase0DisposableTarget')
if ctypes.get_last_error()==183:
    user=ctypes.WinDLL('user32'); user.FindWindowW.restype=ctypes.c_void_p
    handle=user.FindWindowW(None,'Autumn disposable target')
    if handle: user.PostMessageW(ctypes.c_void_p(handle),0x8001,0,0)
    raise SystemExit(0 if handle else 1)

class Target(QWidget):
    def __init__(self):
        super().__init__(); self.handoffs=0; self.setWindowTitle('Autumn disposable target')
        layout=QVBoxLayout(self); layout.addWidget(QLabel('Click the empty edit field for focus tests. No text is saved.'))
        layout.addWidget(QLineEdit()); self.resize(520,130); self.save()
    def save(self):
        (ROOT/'docs/reports/target_probe.json').write_text(json.dumps({'handoffs':self.handoffs,'text_saved':False}),encoding='utf-8')
    def nativeEvent(self,event_type,message):
        msg=wintypes.MSG.from_address(int(message))
        if msg.message==0x8001: self.handoffs+=1; self.save(); return True,0
        return False,0

if __name__=='__main__':
    app=QApplication(sys.argv); window=Target(); window.show(); raise SystemExit(app.exec())
