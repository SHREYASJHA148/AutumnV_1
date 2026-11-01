"""Windows APIs behind the engine boundary. No shell text is ever evaluated."""
from __future__ import annotations

import asyncio
import ctypes
import os
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

from autumn.actions.catalog import (
    BLOCKED_EXECUTABLES,
    AppEntry,
    fingerprint,
    no_reparse,
    validate_app,
)
from autumn.actions.engine import Outcome
from autumn.winworker.cache import configure
from autumn.winworker.capture import screenshot
from autumn.winworker.search import search


def visible_windows() -> dict[int, int]:
    user = ctypes.WinDLL("user32")
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    windows = {}
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def collect(hwnd, _):
        if user.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            windows[int(hwnd)] = pid.value
        return True

    user.EnumWindows(collect, 0)
    return windows


def interactive_desktop() -> bool:
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user.OpenInputDesktop.restype = wintypes.HANDLE
    user.CloseDesktop.argtypes = [wintypes.HANDLE]
    user.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                               wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    handle = user.OpenInputDesktop(0, False, 1)
    if not handle:
        return False
    try:
        name = ctypes.create_unicode_buffer(256)
        size = wintypes.DWORD()
        return bool(user.GetUserObjectInformationW(handle, 2, name, ctypes.sizeof(name), ctypes.byref(size))) and name.value.casefold() == "default"
    finally:
        user.CloseDesktop(handle)


def activate_package(identity: str) -> int:
    from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
    from comtypes.client import CreateObject

    class ActivationManager(IUnknown):
        _iid_ = GUID("{2e941141-7f97-4756-ba1d-9decde894a3d}")
        _methods_ = [COMMETHOD([], HRESULT, "ActivateApplication",
            (["in"], wintypes.LPCWSTR, "identity"), (["in"], wintypes.LPCWSTR, "arguments"),
            (["in"], wintypes.DWORD, "options"), (["out"], ctypes.POINTER(wintypes.DWORD), "pid"))]

    manager = CreateObject(GUID("{45ba127d-10a8-46ea-8ab7-56ea9078943c}"), interface=ActivationManager)
    return int(manager.ActivateApplication(identity, None, 2))


def shortcut_target(path: Path) -> Path:
    import win32com.client
    shortcut = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(path))
    target = no_reparse(Path(shortcut.TargetPath))
    if shortcut.Arguments.strip() or target.suffix.lower() != ".exe" or target.stem.casefold() in BLOCKED_EXECUTABLES:
        raise ValueError("Unsupported shortcut target")
    return target


def import_apps(checkpoint, *, menu_roots=None, include_packages=True) -> tuple[AppEntry, ...]:
    import hashlib
    include_paths = menu_roots is None
    if menu_roots is None:
        menu_roots = [Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs",
                      Path(os.environ["PROGRAMDATA"]) / "Microsoft/Windows/Start Menu/Programs"]
    apps = {}
    for root in menu_roots:
        if not root.exists():
            continue
        count = 0
        for directory, children, files in os.walk(root, followlinks=False):
            if not checkpoint():
                raise InterruptedError()
            children[:] = [name for name in children if not (Path(directory) / name).is_symlink() and not (getattr((Path(directory) / name).lstat(), "st_file_attributes", 0) & 0x400)]
            for filename in files:
                count += 1
                if count > 3000 or len(apps) >= 400:
                    break
                if not checkpoint():
                    raise InterruptedError()
                path = Path(directory) / filename
                if path.suffix.casefold() != ".lnk":
                    continue
                try:
                    no_reparse(path)
                    shortcut_target(path)
                    identifier = "a-" + hashlib.sha256(str(path).casefold().encode()).hexdigest()[:20]
                    apps[identifier] = AppEntry(id=identifier, name=path.stem[:80], kind="shortcut", target=str(path), fingerprint=fingerprint(path))
                except Exception:
                    continue
            if count > 3000 or len(apps) >= 400:
                break
    if include_paths and checkpoint():
        from autumn.winworker.discovery import app_paths
        for entry in app_paths(checkpoint):
            if len(apps) < 500:
                apps.setdefault(entry.id,entry)
    if include_packages and checkpoint():
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            for item in shell.NameSpace("shell:AppsFolder").Items():
                if not checkpoint():
                    raise InterruptedError()
                if len(apps) >= 500:
                    break
                identity = item.ExtendedProperty("System.AppUserModel.ID")
                if not identity or "!" not in identity:
                    continue
                identifier = "p-" + hashlib.sha256(identity.encode()).hexdigest()[:20]
                try:
                    apps[identifier] = validate_app(AppEntry(id=identifier, name=str(item.Name)[:80], kind="package", target=identity))
                except ValueError:
                    continue
        except InterruptedError:
            raise
        except Exception:
            pass
    return tuple(sorted(apps.values(), key=lambda a: a.name.casefold()))


class WindowsAdapter:
    def __init__(self, *, capture=screenshot, data_dir=None):
        from autumn.winworker.dictation import Dictation
        self.dictation = Dictation()
        self.engine = None
        self.capture = capture
        self.data_dir = data_dir
        self.cache_configured = False

    def perform(self, resolved, permit, checkpoint) -> Outcome:
        if permit.outcome != "allow" or not checkpoint():
            return Outcome(status="cancelled", code="CANCELLED", message="Stopped before dispatch.", verification="generation")
        if not interactive_desktop():
            return Outcome(status="failed", code="DENIED", message="Desktop locked or unavailable. No action was dispatched.", verification="input desktop")
        if not self.cache_configured:
            from autumn.storage.settings import app_directory
            configure(self.data_dir or app_directory())
            self.cache_configured = True
        skill, args = resolved.action.skill, resolved.action.arguments
        if skill == "text.type":
            return self.dictation.type_text(resolved.target, args.text, checkpoint)
        if skill == "app.open":
            return self.launch_app(resolved.target, checkpoint)
        if skill == "folder.open":
            os.startfile(str(no_reparse(resolved.target)), "open")
            return Outcome(status="unverified", code="HANDOFF", message="Folder handed to Explorer; its window is unverified.", verification="shell handoff")
        if skill == "website.open":
            # ShellExecute treats the separately supplied, validated URL as data, not command text.
            os.startfile(resolved.target, "open")
            return Outcome(status="unverified", code="HANDOFF", message="Address handed to your browser; page load is unverified.", verification="browser handoff")
        if skill in {"audio.set_volume", "audio.set_mute"}:
            import comtypes
            from pycaw.pycaw import AudioUtilities
            comtypes.CoInitialize()
            try:
                endpoint = AudioUtilities.GetSpeakers().EndpointVolume
                if not checkpoint():
                    raise InterruptedError()
                if skill == "audio.set_volume":
                    endpoint.SetMasterVolumeLevelScalar(args.percent / 100, None)
                    ok = abs(endpoint.GetMasterVolumeLevelScalar() * 100 - args.percent) < 1
                    message = f"Volume set to {args.percent} percent."
                else:
                    endpoint.SetMute(int(args.muted), None)
                    ok = bool(endpoint.GetMute()) == args.muted
                    message = "Speakers muted." if args.muted else "Speakers unmuted."
                return Outcome(status="succeeded" if ok else "unverified", code="OK" if ok else "HANDOFF", message=message if ok else "Audio change sent; read-back did not match.", verification="Core Audio read-back")
            finally:
                comtypes.CoUninitialize()
        if skill == "media.control":
            return asyncio.run(self.media(args.command, checkpoint))
        if skill == "screen.capture":
            artifact = self.capture(resolved.target, args.monitor, checkpoint)
            return Outcome(status="succeeded", code="OK", message="Screenshot saved. Protected content may appear black.", verification="PNG dimensions and file", artifacts=(artifact,))
        if skill == "files.search":
            found = search(resolved.target, args, checkpoint)
            rows = self.engine.register_matches(found.matches)
            details = f"Found {len(rows)} filename matches. {found.backend}."
            if found.limited:
                details += " Partial results: a scan or result limit was reached."
            if found.denied:
                details += f" {found.denied} entries or folders were inaccessible or excluded."
            if found.cancelled:
                details += " Search stopped."
            partial = found.limited or found.denied or found.cancelled
            return Outcome(status="partial" if partial else "succeeded", code="PARTIAL" if partial else "OK", message=details, verification="filename metadata, root boundaries and scan limits", matches=rows)
        return Outcome(status="failed", code="UNSUPPORTED", message="This capability is unavailable.", verification="registry")

    def launch_app(self, entry, checkpoint):
        validate_app(entry)
        before = visible_windows()
        process = None
        pid = 0
        if entry.kind == "executable":
            if not checkpoint():
                raise InterruptedError()
            process = subprocess.Popen([entry.target], shell=False, close_fds=True)
            pid = process.pid
        elif entry.kind in {"shortcut", "file"}:
            if entry.kind == 'shortcut':
                shortcut_target(Path(entry.target))
            if not checkpoint():
                raise InterruptedError()
            import win32api
            import win32process
            from win32com.shell import shell, shellcon
            info = shell.ShellExecuteEx(fMask=shellcon.SEE_MASK_NOCLOSEPROCESS | 0x400 | 0x100,
                                       lpVerb="open", lpFile=entry.target, nShow=1)
            handle = info.get("hProcess")
            if handle:
                try:
                    pid = win32process.GetProcessId(handle)
                finally:
                    win32api.CloseHandle(handle)
        else:
            if not checkpoint():
                raise InterruptedError()
            pid = activate_package(entry.target)
        if not pid and process is None:
            # Windows supplied no process identity, so waiting cannot verify a matching window.
            return Outcome(status="unverified", code="HANDOFF", message="Launch handed to Windows; a new app window was not verified. It may have reused an existing instance.", verification="launch accepted; window unverified")
        until = time.monotonic() + 2
        running_since = time.monotonic()
        while checkpoint() and time.monotonic() < until:
            current = visible_windows()
            if any(hwnd not in before and owner == pid for hwnd, owner in current.items()):
                return Outcome(status="succeeded", code="OK", message="App launch verified by a new window.", verification="new window matched launch PID")
            if process is not None and process.poll() is None and time.monotonic() - running_since >= 0.5:
                return Outcome(status="succeeded", code="OK", message="App process started; its window may still be opening.", verification="created process is running")
            time.sleep(0.04)
        return Outcome(status="unverified", code="HANDOFF", message="Launch handed to Windows; a new app window was not verified. It may have reused an existing instance.", verification="launch accepted; window unverified")

    @staticmethod
    async def media(command, checkpoint):
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Manager,
        )
        manager = await asyncio.wait_for(Manager.request_async(), 3)
        session = manager.get_current_session()
        if session is None:
            return Outcome(status="failed", code="NO_SESSION", message="No active media session is available.", verification="media session manager")
        before = int(session.get_playback_info().playback_status)
        if not checkpoint():
            raise InterruptedError()
        method = {"play_pause": session.try_toggle_play_pause_async, "next": session.try_skip_next_async,
                  "previous": session.try_skip_previous_async}[command]
        accepted = await asyncio.wait_for(method(), 3)
        after = int(session.get_playback_info().playback_status)
        verified = bool(accepted) and command == "play_pause" and before != after
        return Outcome(status="succeeded" if verified else "unverified", code="OK" if verified else "HANDOFF",
            message="Playback state change observed." if verified else "Media request sent; playback delivery is unverified. It will not be retried.", verification="playback state" if verified else "media-session request only")
