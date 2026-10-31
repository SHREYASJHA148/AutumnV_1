"""Match only the activation chord; never store or expose unrelated keyboard input."""

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QTimer


class HoldHook:
    def __init__(self, on_down, on_up):
        self.on_down = on_down
        self.on_up = on_up
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p
        )
        self.user.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            self.callback_type,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self.user.SetWindowsHookExW.restype = ctypes.c_void_p
        self.user.CallNextHookEx.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_size_t,
            ctypes.c_void_p,
        ]
        self.user.CallNextHookEx.restype = ctypes.c_ssize_t
        self.user.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        self.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.handle = None
        self.held = False
        self.callback = None

    def install(self, key):
        self.close()

        @self.callback_type
        def callback(code, event, pointer):
            if code >= 0:
                vk = ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD)).contents.value
                if vk == key:
                    if event in (0x100, 0x104) and not self.held:

                        def pressed(k):
                            return bool(self.user.GetAsyncKeyState(k) & 0x8000)

                        if (
                            pressed(0x11)
                            and pressed(0x12)
                            and not any(pressed(k) for k in (0x10, 0x5B, 0x5C))
                        ):
                            self.held = True
                            QTimer.singleShot(0, self.on_down)
                    elif event in (0x101, 0x105) and self.held:
                        self.held = False
                        QTimer.singleShot(0, self.on_up)
                elif (
                    vk in (0x11, 0x12, 0xA2, 0xA3, 0xA4, 0xA5)
                    and event in (0x101, 0x105)
                    and self.held
                ):
                    self.held = False
                    QTimer.singleShot(0, self.on_up)
            return self.user.CallNextHookEx(self.handle, code, event, pointer)

        self.callback = callback
        self.handle = self.user.SetWindowsHookExW(13, self.callback, None, 0)
        return bool(self.handle)

    def close(self):
        if self.handle:
            self.user.UnhookWindowsHookEx(self.handle)
            self.handle = None
        if self.held:
            self.held = False
            QTimer.singleShot(0, self.on_up)
