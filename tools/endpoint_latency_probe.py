"""Compare endpoint policies on public synthetic speech; no devices or audio files."""
import json
from pathlib import Path

import numpy as np

from autumn.audio.buffer import normalize, speech_stats
from autumn.audio.endpoint import SpeechEndpoint
from autumn.speech.synthesis import Synthesizer

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    audio,rate=Synthesizer().render('Autumn, show capabilities.','',.8,1,lambda:True)
    speech=normalize(audio,rate)
    audio.fill(0)
    pcm=np.concatenate((np.zeros(5600),speech,np.zeros(32000))).astype(np.float32)
    speech.fill(0)
    energy_end=float((np.flatnonzero(np.abs(pcm)>.003)[-1]+1)/16000)
    old_last=0
    old_heard=False
    old_finish=None
    for end in range(1600,len(pcm)+1,1600):
        now=end/16000
        stats=speech_stats(pcm[max(0,end-960):end])
        if stats['voiced_seconds']:
            old_heard=True
            old_last=now
        if old_heard and now-old_last>=.8:
            old_finish=now
            break
    endpoint=SpeechEndpoint()
    new_finish=None
    for end in range(800,len(pcm)+1,800):
        endpoint.feed(pcm[end-800:end])
        if endpoint.finished:
            new_finish=end/16000
            break
    start,end=endpoint.bounds(16000,len(pcm))
    result={'scope':'public synthetic speech; not microphone/room acceptance','old_end_after_energy_seconds':round(old_finish-energy_end,4) if old_finish else None,'new_end_after_energy_seconds':round(new_finish-energy_end,4) if new_finish else None,'saved_seconds':round(old_finish-new_finish,4) if old_finish and new_finish else None,'trimmed_seconds':round((end-start)/16000,3),'recorded_seconds_at_finish':new_finish,'last_energy_preserved':end/16000>=energy_end,'audio_saved':False}
    pcm.fill(0)
    endpoint.discard()
    (root/'docs/reports/latency_endpoint.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
