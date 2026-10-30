"""Read only our own fixture preview LOCALLY; persist labels/booleans, never text."""
import json
import ctypes
from pathlib import Path
import re
import time
from pywinauto import Desktop
from phase0_intent import intent,EXPECTED

ROOT=Path(__file__).resolve().parents[1]
windows=Desktop(backend='uia').windows(title='Autumn — guided Phase 0 validation',visible_only=True)
if len(windows)!=1:raise RuntimeError('Expected exactly one owned fixture window')
window=windows[0]; rows={}; started=time.monotonic()
print('Local semantic observer started; no preview text is logged.',flush=True)
user=ctypes.WinDLL('user32')
while user.IsWindow(window.handle) and time.monotonic()-started<3600:
    for control in window.descendants(control_type='Text'):
        text=control.window_text()
        match=re.match(r'(base\.en|small\.en), previous capture (\d+): (.*)',text,re.S)
        if not match:continue
        size,case,recognized=match.groups(); index=int(case)-1
        if not 0<=index<len(EXPECTED):continue
        key=(size,index)
        if key in rows:continue
        rows[key]={'model':size,'case':index+1,'intended_action_match':intent(recognized)==EXPECTED[index]}
        report={'method':'local deterministic intent grammar; no action dispatch','transcripts_saved':False,
            'rows':list(rows.values()),'base_coverage':sum(k[0]=='base.en' for k in rows),
            'small_coverage':sum(k[0]=='small.en' for k in rows)}
        (ROOT/'docs/reports/owner_semantic_observation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(f'Intent labels observed: {len(rows)}',flush=True)
    time.sleep(.1)
