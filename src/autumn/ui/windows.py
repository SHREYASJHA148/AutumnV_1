"""Native single-instance, shortcut and session notifications; no automation."""
from __future__ import annotations

import ctypes
import hashlib
import mmap
import os
import struct
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QAbstractNativeEventFilter

from autumn.storage.settings import Hotkeys


class SingleInstance:
    def __init__(self, root: Path) -> None:
        key = hashlib.sha256(str(root.resolve()).casefold().encode()).hexdigest()[:24]
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateEventW.restype = wintypes.HANDLE
        for name in ("SetEvent", "ResetEvent", "CloseHandle"):
            getattr(self.kernel, name).argtypes = [wintypes.HANDLE]
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.mutex = self.kernel.CreateMutexW(None, False, f"Local\\Autumn.{key}.mutex")
        if not self.mutex:
            raise OSError("Single-instance guard unavailable")
        self.primary = ctypes.get_last_error() != 183
        self.event = self.kernel.CreateEventW(None, True, False, f"Local\\Autumn.{key}.focus")
        if not self.event:
            self.kernel.CloseHandle(self.mutex)
            raise OSError("Single-instance handoff unavailable")
        self.shared = mmap.mmap(-1, 16, tagname=f"Local\\Autumn.{key}.window")
        if self.primary:
            self.shared[:] = struct.pack("QQ", os.getpid(), 0)

    def publish(self, handle: int) -> None:
        self.shared[:] = struct.pack("QQ", os.getpid(), handle)

    def request_focus(self) -> None:
        pid, _ = struct.unpack("QQ", self.shared[:])
        if pid:
            ctypes.WinDLL("user32").AllowSetForegroundWindow(wintypes.DWORD(pid))
        self.kernel.SetEvent(self.event)

    def focus_requested(self) -> bool:
        if self.kernel.WaitForSingleObject(self.event, 0) == 0:
            self.kernel.ResetEvent(self.event)
            return True
        return False

    def close(self) -> None:
        self.shared.close()
        self.kernel.CloseHandle(self.event)
        self.kernel.CloseHandle(self.mutex)


CHORDS = {
    "Ctrl+Alt+Backspace": (0x4003, 0x08),
    "Ctrl+Alt+Space": (0x4003, 0x20),
    "Ctrl+Alt+F9": (0x4003, 0x78),
    "Ctrl+Alt+F10": (0x4003, 0x79),
}


class NativeEvents(QAbstractNativeEventFilter):
    def __init__(self, on_stop, on_voice, on_suspend, on_resume) -> None:
        super().__init__()
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.wts = ctypes.WinDLL("wtsapi32")
        self.wts.WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
        self.wts.WTSUnRegisterSessionNotification.argtypes = [wintypes.HWND]
        self.callbacks = {0xA101: on_stop, 0xA102: on_voice}
        self.on_suspend = on_suspend
        self.on_resume = on_resume
        self.registered: list[int] = []
        self.window: int | None = None
        self.session_registered = False

    def bind_window(self, handle: int) -> None:
        self.window = handle
        self.session_registered = bool(self.wts.WTSRegisterSessionNotification(handle, 0))

    def register(self, settings: Hotkeys) -> list[dict[str, str]]:
        self.unregister()
        rows = []
        for identifier, name, chord in (
            (0xA101, "Stop shortcut", settings.stop),
            (0xA102, "Voice readiness shortcut", settings.voice_toggle),
        ):
            mods, key = CHORDS[chord]
            ok = bool(self.user.RegisterHotKey(None, identifier, mods, key))
            if ok:
                self.registered.append(identifier)
            rows.append({"name": name, "detail": f"{chord}: {'registered' if ok else 'unavailable — use the on-screen button'}"})
        return rows

    def unregister(self) -> None:
        for identifier in self.registered:
            self.user.UnregisterHotKey(None, identifier)
        self.registered.clear()

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) not in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            return False, 0
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam in self.registered:
            self.callbacks[msg.wParam]()
            return True, 0
        if self.window is not None and msg.hWnd == self.window:
            if msg.message == 0x02B1:  # WM_WTSSESSION_CHANGE
                if msg.wParam == 7:
                    self.on_suspend()
                elif msg.wParam == 8:
                    self.on_resume()
            elif msg.message == 0x0218:  # WM_POWERBROADCAST
                if msg.wParam == 4:
                    self.on_suspend()
                elif msg.wParam in (7, 18):
                    self.on_resume()
        return False, 0

    def close(self) -> None:
        self.unregister()
        if self.session_registered:
            self.wts.WTSUnRegisterSessionNotification(self.window)
