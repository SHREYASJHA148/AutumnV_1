"""Disposable integration target, available only through the explicit diagnostic CLI."""

import json
import os

import win32api
import win32con
import win32gui


def run(ready):
    instance = win32api.GetModuleHandle(None)

    def procedure(hwnd, message, wparam, lparam):
        if message == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, message, wparam, lparam)

    cls = win32gui.WNDCLASS()
    cls.hInstance = instance
    cls.lpszClassName = "AutumnDisposableDictation"
    cls.lpfnWndProc = procedure
    atom = win32gui.RegisterClass(cls)
    window = win32gui.CreateWindow(
        atom,
        "Autumn disposable dictation target",
        win32con.WS_OVERLAPPEDWINDOW,
        100,
        100,
        620,
        300,
        0,
        0,
        instance,
        None,
    )
    edit = win32gui.CreateWindow(
        "EDIT",
        "",
        win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.WS_BORDER | win32con.ES_AUTOHSCROLL,
        20,
        30,
        540,
        40,
        window,
        1,
        instance,
        None,
    )
    password = win32gui.CreateWindow(
        "EDIT",
        "",
        win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.WS_BORDER | win32con.ES_PASSWORD,
        20,
        100,
        540,
        40,
        window,
        2,
        instance,
        None,
    )
    steal = win32gui.CreateWindow(
        atom,
        "Autumn disposable focus target",
        win32con.WS_OVERLAPPEDWINDOW,
        750,
        100,
        300,
        180,
        0,
        0,
        instance,
        None,
    )
    win32gui.ShowWindow(window, win32con.SW_SHOWNORMAL)
    win32gui.ShowWindow(steal, win32con.SW_SHOWNOACTIVATE)
    try:
        win32gui.SetForegroundWindow(window)
        win32gui.SetFocus(edit)
    except Exception:
        pass  # The driver requests focus only after it owns a visible foreground window.
    ready.parent.mkdir(parents=True, exist_ok=True)
    ready.write_text(
        json.dumps(
            {
                "window": window,
                "edit": edit,
                "password": password,
                "steal": steal,
                "pid": os.getpid(),
            }
        ),
        encoding="utf-8",
    )
    win32gui.PumpMessages()
    return 0
