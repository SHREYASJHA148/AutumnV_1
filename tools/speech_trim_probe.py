"""Check trimming on synthetic 48 kHz capture data with the unchanged speech model."""
import json
import logging
import re
from pathlib import Path

import numpy as np

from autumn.audio.buffer import normalize, resample
from autumn.audio.endpoint import SpeechEndpoint
from autumn.speech.recognition import Recognizer
from autumn.speech.synthesis import Synthesizer

if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    root=Path(__file__).resolve().parents[1]
    synthesis=Synthesizer()
    recognition=Recognizer()
    result={'scope':'public synthetic speech at simulated native capture rate; no audio hardware or actions','source_rate':48000,'cases':[]}
    for phrase in ('Autumn, show capabilities.','Autumn, mute speakers.','Autumn, open a folder.'):
        audio,rate=synthesis.render(phrase,'',.8,1,lambda:True)
        native=resample(audio,rate,48000)
        audio.fill(0)
        stream=np.concatenate((np.zeros(24000),native,np.zeros(72000))).astype(np.float32)
        native.fill(0)
        endpoint=SpeechEndpoint()
        finish=len(stream)
        for offset in range(0,len(stream),2400):
            normalized=normalize(stream[offset:offset+2400],48000)
            endpoint.feed(normalized)
            normalized.fill(0)
            if endpoint.finished:
                finish=min(len(stream),offset+2400)
                break
        start,end=endpoint.bounds(48000,finish)
        pcm=normalize(stream[start:end],48000)
        recognized=recognition.transcribe(pcm.astype('<f4').tobytes(),'small.en','',lambda:True)
        pcm.fill(0)
        stream.fill(0)
        endpoint.discard()
        exact=recognized['accepted'] and re.sub('[^a-z]','',recognized['text'].casefold())==re.sub('[^a-z]','',phrase.casefold())
        result['cases'].append({'index':len(result['cases']),'accepted':recognized['accepted'],'exact':exact,'trimmed_seconds':round((end-start)/48000,3)})
        (root/'docs/reports/latency_trim_quality.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result['cases'][-1]),flush=True)
    result['passed']=all(c['exact'] for c in result['cases'])
    (root/'docs/reports/latency_trim_quality.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
