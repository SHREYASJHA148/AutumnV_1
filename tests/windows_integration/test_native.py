import ctypes
from ctypes import wintypes

from PySide6.QtCore import QCoreApplication

from autumn.storage.settings import Hotkeys
from autumn.ui.windows import NativeEvents, SingleInstance


def test_single_instance_handoff_and_reacquisition(tmp_path):
    first = SingleInstance(tmp_path / "instance é")
    second = SingleInstance(tmp_path / "instance é")
    try:
        assert first.primary and not second.primary
        second.request_focus()
        assert first.focus_requested()
        assert not first.focus_requested()
    finally:
        second.close()
        first.close()
    third = SingleInstance(tmp_path / "instance é")
    try:
        assert third.primary
    finally:
        third.close()


def test_shortcut_conflict_and_native_message_delivery():
    app = QCoreApplication.instance() or QCoreApplication([])
    calls = []
    native = NativeEvents(lambda: calls.append("stop"), lambda: calls.append("voice"),
                          lambda: calls.append("suspend"), lambda: calls.append("resume"))
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    assert user.RegisterHotKey(None, 0xA201, 0x4003, 0x78)
    try:
        rows = native.register(Hotkeys(stop="Ctrl+Alt+F9", voice_toggle="Ctrl+Alt+F10"))
        assert "unavailable" in rows[0]["detail"]
        assert "on-screen button" in rows[0]["detail"]
        assert "registered" in rows[1]["detail"]
        app.installNativeEventFilter(native)
        user.PostThreadMessageW(ctypes.WinDLL("kernel32").GetCurrentThreadId(), 0x0312, 0xA102, 0)
        for _ in range(10):
            app.processEvents()
        assert calls == ["voice"]
    finally:
        app.removeNativeEventFilter(native)
        native.close()
        user.UnregisterHotKey(None, 0xA201)
    assert native.registered == []
