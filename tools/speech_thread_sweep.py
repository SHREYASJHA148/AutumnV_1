"""Interleaved thread-count comparison on identical public synthetic PCM."""
import json
import logging
import re
import time
from pathlib import Path

import numpy as np

from autumn.audio.buffer import normalize
from autumn.speech.recognition import Recognizer
from autumn.speech.synthesis import Synthesizer

if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    root=Path(__file__).resolve().parents[1]
    report=root/'docs/reports/latency_thread_sweep.json'
    phrase='Autumn, show capabilities.'
    audio,rate=Synthesizer().render(phrase,'',.8,1,lambda:True)
    pcm=normalize(audio,rate).astype('<f4').tobytes()
    audio.fill(0)
    recognizer=Recognizer()
    recognizer.transcribe(pcm,'small.en','',lambda:True)
    result={'scope':'interleaved CPU threads on identical synthetic speech, unchanged small.en/confidence rules; no hardware/actions','cases':[]}
    for threads in (4,6,8,8,6,4):
        recognizer.model._set_params({'n_threads':threads})
        started=time.perf_counter()
        response=recognizer.transcribe(pcm,'small.en','',lambda:True)
        row={'threads':threads,'seconds':round(time.perf_counter()-started,4),'accepted':response['accepted'],'exact':response['accepted'] and re.sub('[^a-z]','',response['text'].casefold())==re.sub('[^a-z]','',phrase.casefold())}
        result['cases'].append(row)
        report.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(row),flush=True)
    result['medians']={str(t):round(float(np.median([r['seconds'] for r in result['cases'] if r['threads']==t])),4) for t in (4,6,8)}
    result['complete']=True
    report.write_text(json.dumps(result,indent=2),encoding='utf-8')
