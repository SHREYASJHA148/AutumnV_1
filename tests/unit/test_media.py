import asyncio
import sys
import types

from autumn.winworker.windows import WindowsAdapter


def test_uncertain_media_delivery_is_unverified_and_not_retried(monkeypatch):
    calls = []
    class Session:
        def get_playback_info(self):
            return types.SimpleNamespace(playback_status=4)

        async def try_toggle_play_pause_async(self):
            calls.append("toggle")
            return True

        async def try_skip_next_async(self):
            calls.append("next")
            return True

        async def try_skip_previous_async(self):
            calls.append("previous")
            return True

    class Manager:
        @staticmethod
        async def request_async():
            return types.SimpleNamespace(get_current_session=lambda: Session())

    module = types.ModuleType("winrt.windows.media.control")
    module.GlobalSystemMediaTransportControlsSessionManager = Manager
    monkeypatch.setitem(sys.modules, "winrt.windows.media.control", module)
    for command in ("play_pause", "next", "previous"):
        result = asyncio.run(WindowsAdapter.media(command, lambda: True))
        assert result.status == "unverified" and result.code == "HANDOFF"
    assert calls == ["toggle", "next", "previous"]
