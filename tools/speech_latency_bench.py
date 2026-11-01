"""Public synthetic development PCM only; no hardware, files of audio or actions."""
import argparse
import json
import logging
import re
import time
from pathlib import Path

import numpy as np

from autumn.audio.buffer import normalize
from autumn.speech.recognition import Recognizer
from autumn.speech.synthesis import Synthesizer

PHRASES=('Autumn, show capabilities.','Autumn, mute speakers.','Autumn, open a folder.')


def canonical(text):
    return re.sub('[^a-z0-9]','',text.casefold())


def main():
    logging.disable(logging.CRITICAL)
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--threads',type=int,default=4)
    args=parser.parse_args()
    result={'scope':'three public synthetic development commands; same small.en CPU model, no microphone/playback/actions','threads':args.threads,'cases':[]}
    synthesis=Synthesizer()
    recognizer=Recognizer()
    recognizer.threads=args.threads
    for phrase in PHRASES:
        started=time.perf_counter()
        audio,rate=synthesis.render(phrase,'',.8,1,lambda:True)
        synthesis_s=time.perf_counter()-started
        pcm=normalize(audio,rate)
        audio.fill(0)
        # Load once using the production adapter, then vary only the supported thread setting.
        if recognizer.model is not None:
            recognizer.model._set_params({'n_threads':args.threads})
        before=time.perf_counter()
        recognized=recognizer.transcribe(pcm.astype('<f4').tobytes(),'small.en','',lambda:True)
        elapsed=time.perf_counter()-before
        pcm.fill(0)
        result['cases'].append({'index':len(result['cases']),'synthesis_seconds':round(synthesis_s,4),'recognition_seconds':round(elapsed,4),'accepted':recognized['accepted'],'exact':recognized['accepted'] and canonical(recognized['text'])==canonical(phrase)})
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result['cases'][-1]),flush=True)
    result['complete']=True
    result['warm_recognition_median_seconds']=round(float(np.median([c['recognition_seconds'] for c in result['cases'][1:]])),4)
    args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
