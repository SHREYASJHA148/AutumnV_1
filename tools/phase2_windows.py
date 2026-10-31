"""Local native action trial. No personal file search, browser navigation or media toggles."""
from __future__ import annotations

import asyncio
import ctypes
import json
import time
from ctypes import wintypes
from pathlib import Path

from autumn.actions.catalog import AppEntry, FolderEntry, fingerprint
from autumn.actions.engine import Engine
from autumn.actions.router import route
from autumn.actions.schemas import CaptureScreen, Plan
from autumn.controller.contracts import Request
from autumn.storage.settings import Settings
from autumn.winworker.capture import screenshot
from autumn.winworker.windows import WindowsAdapter, import_apps

ROOT = Path(__file__).resolve().parents[1]


def run():
    import comtypes
    from pycaw.pycaw import AudioUtilities
    comtypes.CoInitialize()
    fixture = ROOT / ".cache/phase2 native é"
    fixture.mkdir(parents=True, exist_ok=True)
    exe = ROOT / "dist/phase2 fixture é/AutumnDisposable/AutumnDisposable.exe"
    user = ctypes.WinDLL("user32")
    user.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user.FindWindowW.restype = wintypes.HWND
    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user.GetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
    user.GetPropW.restype = wintypes.HANDLE
    if user.FindWindowW("AutumnPhase2DisposableClass", None):
        raise RuntimeError("Disposable fixture already open; do not touch an unowned instance")
    entry = AppEntry(id="fixture", name="Fixture", kind="executable", target=str(exe), fingerprint=fingerprint(exe), reviewed=True, enabled=True)
    settings = Settings(apps=(entry,), folders=(FolderEntry(id="fixtures", name="Fixtures", path=str(fixture)),), screenshot_folder=str(fixture / "captures"))
    adapter = WindowsAdapter(data_dir=fixture)
    engine = Engine(adapter, settings)
    adapter.engine = engine
    report = {"personal_files_searched": False, "browser_opened": False, "media_toggled": False}

    def execute(text):
        plan = route(text, engine.settings).plan
        assert plan is not None
        return engine.execute(plan, Request(generation=0), lambda: True, lambda *_: None)[0]

    hwnd = None
    endpoint = None
    before_volume = before_mute = None
    try:
        first = execute("open fixture")
        until = time.monotonic() + 5
        while time.monotonic() < until and not hwnd:
            hwnd = user.FindWindowW("AutumnPhase2DisposableClass", None)
            time.sleep(0.03)
        assert hwnd and first.status == "succeeded"
        report["executable_launch"] = first.model_dump(exclude={"artifacts", "matches"})
        second = execute("open fixture")
        assert second.status == "unverified"
        assert user.GetPropW(hwnd, "AutumnHandoffs") == 1
        report["single_instance_handoff"] = second.model_dump(exclude={"artifacts", "matches"})

        import win32com.client
        menus = fixture / "Start Menu"
        menus.mkdir(exist_ok=True)
        shortcut_path = menus / "Fixture shortcut.lnk"
        shortcut = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(shortcut_path))
        shortcut.TargetPath = str(exe)
        shortcut.Save()
        imported = import_apps(lambda: True, menu_roots=[menus], include_packages=False)
        assert len(imported) == 1 and not imported[0].enabled and not imported[0].reviewed
        selected = imported[0].model_copy(update={"enabled": True, "reviewed": True})
        engine.settings = settings.model_copy(update={"apps": (entry, selected)})
        launched = execute("open fixture shortcut")
        assert launched.status == "unverified"
        report["shortcut_import_and_launch"] = True
        report["shortcut_handoffs"] = int(user.GetPropW(hwnd, "AutumnHandoffs") or 0)

        rect = wintypes.RECT()
        user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user.GetClientRect(hwnd, ctypes.byref(rect))
        adapter.capture = lambda folder, monitor, check: screenshot(folder, monitor, check,
            bounds=(0,0,rect.right,rect.bottom), source_window=hwnd)
        capture = engine.execute(Plan(steps=(CaptureScreen(),)), Request(generation=0), lambda: True, lambda *_: None)[0]
        assert capture.status == "succeeded"
        report["owned_window_capture"] = {"status": capture.status, "width": capture.artifacts[0]["width"], "height": capture.artifacts[0]["height"]}

        (fixture / "budget é.xlsx").write_text("Disposable filename fixture; no content search.", encoding="utf-8")
        found = execute("find spreadsheet budget in fixtures")
        assert found.status in {"succeeded", "partial"} and len(found.matches) == 1
        report["filename_search"] = {"status": found.status, "matches": len(found.matches), "backend": "bounded scan if index/coverage unavailable"}

        endpoint = AudioUtilities.GetSpeakers().EndpointVolume
        before_volume, before_mute = endpoint.GetMasterVolumeLevelScalar(), endpoint.GetMute()
        volume = execute(f"set volume to {round(before_volume * 100)} percent")
        mute = execute("mute" if before_mute else "unmute")
        assert volume.status == mute.status == "succeeded"
        report["audio_readback"] = True
        async def media_presence():
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
            manager = await Manager.request_async()
            return len(manager.get_sessions())
        sessions = asyncio.run(media_presence())
        report["media_sessions"] = sessions
        if sessions == 0:
            media = execute("play pause")
            assert media.code == "NO_SESSION"
            report["no_media_session_result"] = media.code
        else:
            report["no_media_session_result"] = "not tested: active owner session left unchanged"
        report["passed"] = True
    finally:
        if endpoint is not None:
            endpoint.SetMasterVolumeLevelScalar(before_volume, None)
            endpoint.SetMute(before_mute, None)
        if hwnd:
            user.PostMessageW(hwnd, 0x0010, 0, 0)
        comtypes.CoUninitialize()
        (ROOT / "docs/reports/phase2_native.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"native_passed":report.get("passed",False)}))


if __name__ == "__main__":
    run()
