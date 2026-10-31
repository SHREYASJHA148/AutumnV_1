"""Conservative native Edit/RichEdit support; no clipboard, shortcuts or retries."""

import ctypes
import time
from ctypes import wintypes as W
from dataclasses import asdict, dataclass
from uuid import uuid4

import win32api
import win32con
import win32gui
import win32process
import win32security

from autumn.actions.engine import Outcome
from autumn.actions.schemas import TextArgs


@dataclass(frozen=True)
class Target:
    window: int
    control: int
    pid: int
    created: str
    title: str
    control_class: str


class GUIThread(ctypes.Structure):
    _fields_ = [
        ("size", W.DWORD),
        ("flags", W.DWORD),
        *[(n, W.HWND) for n in ("active", "focus", "capture", "menu", "move", "caret")],
        ("rect", W.RECT),
    ]


class KeyInput(ctypes.Structure):
    _fields_ = [
        ("vk", W.WORD),
        ("scan", W.WORD),
        ("flags", W.DWORD),
        ("time", W.DWORD),
        ("extra", ctypes.c_size_t),
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", W.LONG),
        ("dy", W.LONG),
        ("data", W.DWORD),
        ("flags", W.DWORD),
        ("time", W.DWORD),
        ("extra", ctypes.c_size_t),
    ]


class InputUnion(ctypes.Union):
    _fields_ = [("keyboard", KeyInput), ("mouse", MouseInput)]


class Input(ctypes.Structure):
    _anonymous_ = ("payload",)
    _fields_ = [("type", W.DWORD), ("payload", InputUnion)]


def identity(pid):
    process = win32api.OpenProcess(0x1000, False, pid)
    try:
        token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
        try:
            sid = win32security.GetTokenInformation(token, win32security.TokenIntegrityLevel)[0]
            level = sid.GetSubAuthority(sid.GetSubAuthorityCount() - 1)
            if level >= 0x3000:
                raise PermissionError("Elevated target refused")
        finally:
            token.Close()
        return str(win32process.GetProcessTimes(process)["CreationTime"])
    finally:
        process.Close()


class Dictation:
    def __init__(self):
        self.targets = {}
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.user.GetForegroundWindow.restype = W.HWND
        self.user.GetAncestor.argtypes = [W.HWND, W.UINT]
        self.user.GetAncestor.restype = W.HWND
        self.user.GetGUIThreadInfo.argtypes = [W.DWORD, ctypes.POINTER(GUIThread)]
        self.user.SendInput.argtypes = [W.UINT, ctypes.POINTER(Input), ctypes.c_int]

    def snapshot(self, window, control):
        if not all(
            win32gui.IsWindow(h) and win32gui.IsWindowVisible(h) and win32gui.IsWindowEnabled(h)
            for h in (window, control)
        ):
            raise ValueError("Target unavailable")
        thread, pid = win32process.GetWindowThreadProcessId(window)
        if (
            win32process.GetWindowThreadProcessId(control)[1] != pid
            or self.user.GetAncestor(control, 2) != window
        ):
            raise ValueError("Control changed")
        name = win32gui.GetClassName(control)
        if name.casefold() != "edit" and not name.casefold().startswith("richedit"):
            raise ValueError("Unsupported control")
        if win32gui.GetWindowLong(control, -16) & (0x20 | 0x800):
            raise PermissionError("Password or read-only field refused")
        return Target(
            window, control, pid, identity(pid), win32gui.GetWindowText(window)[:200], name
        )

    def enumerate(self):
        self.targets.clear()
        rows = []

        def window(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
                return

            def child(control, _):
                if len(rows) >= 80:
                    return
                try:
                    target = self.snapshot(hwnd, control)
                    token = uuid4().hex
                    self.targets[token] = (target, time.monotonic() + 120)
                    rows.append({"id": token, "label": target.title + " · " + target.control_class})
                except Exception:
                    pass

            win32gui.EnumChildWindows(hwnd, child, None)

        win32gui.EnumWindows(window, None)
        return rows

    def resolve(self, token):
        target, expires = self.targets[token]
        if time.monotonic() > expires or self.snapshot(target.window, target.control) != target:
            raise LookupError("Target changed or expired")
        return target

    def current(self, target, focused=False):
        try:
            if self.snapshot(target.window, target.control) != target:
                return False
            if focused:
                if self.user.GetForegroundWindow() != target.window:
                    return False
                thread = win32process.GetWindowThreadProcessId(target.window)[0]
                info = GUIThread(size=ctypes.sizeof(GUIThread))
                if (
                    not self.user.GetGUIThreadInfo(thread, ctypes.byref(info))
                    or info.focus != target.control
                ):
                    return False
            return True
        except Exception:
            return False

    def snapshot_data(self, target):
        return asdict(target) if self.current(target) else {"changed": True}

    def send_character(self, character):
        units = character.encode("utf-16-le")
        inputs = []
        for index in range(0, len(units), 2):
            unit = int.from_bytes(units[index : index + 2], "little")
            inputs.extend(
                [
                    Input(type=1, keyboard=KeyInput(scan=unit, flags=4)),
                    Input(type=1, keyboard=KeyInput(scan=unit, flags=6)),
                ]
            )
        array = (Input * len(inputs))(*inputs)
        return self.user.SendInput(len(inputs), array, ctypes.sizeof(Input)) == len(inputs)

    def type_text(self, target, text, checkpoint):
        TextArgs(text=text, target_id="validated")
        # The confirm chord must be released before any character is injected.
        until = time.monotonic() + 1.5
        while any(win32api.GetAsyncKeyState(k) & 0x8000 for k in (0x10, 0x11, 0x12, 0x5B, 0x5C)):
            if not checkpoint() or time.monotonic() >= until:
                return Outcome(
                    status="cancelled",
                    code="CANCELLED",
                    message="Release modifier keys and request dictation again. Nothing retried.",
                    verification="modifier guard",
                )
            time.sleep(0.01)
        count = 0
        for character in text:
            if not checkpoint() or not self.current(target, focused=True):
                return Outcome(
                    status="partial" if count else "cancelled",
                    code="PARTIAL" if count else "CANCELLED",
                    message=f"Dictation stopped after {count} characters accepted as input. Remaining text was not retried.",
                    verification="foreground/control guard",
                )
            if not self.send_character(character):
                return Outcome(
                    status="partial",
                    code="PARTIAL",
                    message=f"Input delivery uncertain after {count} complete characters. No retry.",
                    verification="SendInput returned incomplete acceptance",
                )
            count += 1
        return Outcome(
            status="unverified",
            code="OK",
            message=f"{count} characters accepted as input; text delivery is unverified. No Enter or shortcut was sent.",
            verification="Unicode input acceptance, not application acknowledgement",
        )
