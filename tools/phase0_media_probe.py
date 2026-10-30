"""Read media-session states without reading titles or controlling playback."""
import asyncio
import json
from pathlib import Path
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

async def main():
    manager=await asyncio.wait_for(GlobalSystemMediaTransportControlsSessionManager.request_async(),10)
    sessions=list(manager.get_sessions())
    report={'binding':'PyWinRT Windows.Media.Control','session_count':len(sessions),
        'playback_states':[int(s.get_playback_info().playback_status) for s in sessions],
        'playback_changed':False,'media_titles_read':False}
    (Path(__file__).resolve().parents[1]/'docs/reports/media_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__': asyncio.run(main())
