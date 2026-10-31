"""Disposable, self-expiring native window; no input capture or personal data."""
import ctypes
import time
from ctypes import wintypes


def main():
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    gdi = ctypes.WinDLL("gdi32")
    class_name = "AutumnPhase2DisposableClass"
    user.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user.FindWindowW.restype = wintypes.HWND
    existing = user.FindWindowW(class_name, None)
    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    if existing:
        user.PostMessageW(existing, 0x800C, 0, 0)
        return 0
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    user.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user.DefWindowProcW.restype = ctypes.c_ssize_t
    user.DestroyWindow.argtypes = [wintypes.HWND]
    user.SetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE]
    started = time.monotonic()
    handoffs = 0

    @callback_type
    def procedure(hwnd, message, wparam, lparam):
        nonlocal handoffs
        if message == 0x800C:
            handoffs += 1
            user.SetPropW(hwnd, "AutumnHandoffs", ctypes.c_void_p(handoffs))
            return 0
        if message == 0x0113 and time.monotonic() - started > 45:
            user.DestroyWindow(hwnd)
            return 0
        if message == 2:
            user.PostQuitMessage(0)
            return 0
        return user.DefWindowProcW(hwnd, message, wparam, lparam)

    class WindowClass(ctypes.Structure):
        _fields_ = [("style", wintypes.UINT), ("procedure", callback_type), ("class_extra", ctypes.c_int),
                    ("window_extra", ctypes.c_int), ("instance", wintypes.HINSTANCE), ("icon", wintypes.HICON),
                    ("cursor", wintypes.HANDLE), ("background", wintypes.HBRUSH), ("menu", wintypes.LPCWSTR), ("name", wintypes.LPCWSTR)]

    kernel.GetModuleHandleW.restype = wintypes.HMODULE
    gdi.CreateSolidBrush.argtypes = [wintypes.DWORD]
    gdi.CreateSolidBrush.restype = wintypes.HBRUSH
    brush = gdi.CreateSolidBrush(0x003c5020)
    instance = kernel.GetModuleHandleW(None)
    wc = WindowClass(0, procedure, 0, 0, instance, None, None, brush, None, class_name)
    user.RegisterClassW(ctypes.byref(wc))
    user.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
    user.CreateWindowExW.restype = wintypes.HWND
    hwnd = user.CreateWindowExW(0, class_name, "Autumn disposable Phase 2 target", 0x10CF0000, 100, 100, 440, 260, None, None, instance, None)
    if not hwnd:
        return 1
    user.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
    user.SetTimer(hwnd, 1, 1000, None)
    msg = wintypes.MSG()
    while user.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user.TranslateMessage(ctypes.byref(msg))
        user.DispatchMessageW(ctypes.byref(msg))
    gdi.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi.DeleteObject(brush)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
