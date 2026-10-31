import ctypes
from pathlib import Path
from types import SimpleNamespace

import pytest
import win32com.client
from PySide6.QtCore import QCoreApplication

from autumn.audio.hotkeys import HoldHook
from autumn.speech.workers import windows_speak
from autumn.winworker import cache


def test_hold_hook_ignores_unrelated_keys_repeats_and_releases_on_modifier_up():
    app = QCoreApplication.instance() or QCoreApplication([])
    calls = []
    hook = HoldHook(lambda: calls.append("down"), lambda: calls.append("up"))
    hook.user = SimpleNamespace(
        SetWindowsHookExW=lambda *args: 123,
        UnhookWindowsHookEx=lambda handle: True,
        CallNextHookEx=lambda *args: 0,
        GetAsyncKeyState=lambda key: 0x8000 if key in (0x11, 0x12) else 0,
    )
    assert hook.install(0x20)
    try:
        for key, event in ((0x41, 0x100), (0x20, 0x100), (0x20, 0x100), (0x42, 0x101), (0xA2, 0x101)):
            data = ctypes.c_ulong(key)
            hook.callback(0, event, ctypes.addressof(data))
        app.processEvents()
        assert calls == ["down", "up"] and not hook.held
    finally:
        hook.close()


@pytest.mark.parametrize("female, cancel", [(True, False), (True, True), (False, False)])
def test_windows_female_fallback_uses_memory_and_honors_cancellation(monkeypatch, tmp_path, female, cancel):
    spoken = []
    token = SimpleNamespace(GetDescription=lambda: "Microsoft Zira English" if female else "Male English")
    voice = SimpleNamespace(GetVoices=lambda: [token], Speak=lambda text, flags: spoken.append((text, flags)), WaitUntilDone=lambda timeout: not cancel)
    monkeypatch.setattr(cache, "configure", lambda root: None)
    monkeypatch.setattr(win32com.client, "Dispatch", lambda name: voice)
    checkpoints = iter([True, False, False])
    check = (lambda: next(checkpoints)) if cancel else (lambda: True)
    if not female:
        with pytest.raises(RuntimeError):
            windows_speak("Public test.", 0.5, 1, check, Path(tmp_path))
        assert not spoken
    elif cancel:
        with pytest.raises(InterruptedError):
            windows_speak("Public test.", 0.5, 1, check, Path(tmp_path))
        assert spoken[-1] == ("", 3)
    else:
        windows_speak("First. Second. Third.", 0.5, 1, check, Path(tmp_path))
        assert spoken == [("First. Second.", 3)] and voice.Volume == 50
    assert not list(tmp_path.iterdir())
