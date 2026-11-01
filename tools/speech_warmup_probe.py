"""Prime real speech workers and measure a later request; no audio devices opened."""
import json
import time
from pathlib import Path
from uuid import uuid4

import numpy as np

from autumn.audio.buffer import normalize
from autumn.speech.service import SpeechService

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    service=SpeechService(root/'.cache/latency-warmup')
    result={'audio_hardware_opened':False,'audio_saved':False,'actions':0}
    start=time.perf_counter()
    ready=set()
    try:
        service.send('recognition','warm')
        service.send('playback','warm')
        deadline=time.monotonic()+45
        while ready!={'recognition','playback'}:
            if time.monotonic()>deadline:
                raise TimeoutError()
            for event in service.poll():
                if event['kind'] in {'speech_error','worker_failed','speech_warm_error'}:
                    raise RuntimeError(event['kind'])
                if event['kind']=='speech_warmed':
                    ready.add(event['role'])
                    result[event['role']+'_ready_seconds']=round(time.perf_counter()-start,3)
            time.sleep(.01)
        then=time.perf_counter()
        service.send('playback','synthesize',text='Autumn, show capabilities.')
        stage='synthesize'
        operation=uuid4()
        while stage!='done':
            if time.monotonic()>deadline:
                raise TimeoutError()
            for event in service.poll():
                if event['kind'] in {'speech_error','worker_failed'}:
                    raise RuntimeError(event['kind'])
                if event['kind']=='synthesized':
                    result['primed_synthesis_seconds']=round(time.perf_counter()-then,3)
                    pcm=normalize(np.frombuffer(event['pcm'],dtype='<f4'),event['sample_rate'])
                    then=time.perf_counter()
                    service.send('recognition','transcribe',operation_id=operation,pcm=pcm.astype('<f4').tobytes())
                    pcm.fill(0)
                    stage='recognize'
                if event['kind']=='recognized':
                    result['primed_recognition_seconds']=round(time.perf_counter()-then,3)
                    result['accepted']=event['result']['accepted']
                    stage='done'
            time.sleep(.01)
        result['passed']=result['accepted']
    except Exception as error:
        result.update(passed=False,error_type=type(error).__name__)
    finally:
        result['clean_shutdown']=service.shutdown()
    (root/'docs/reports/latency_warmup.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
