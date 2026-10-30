"""Local wake inference over synthetic silence/noise, no microphone capture."""
import json
from pathlib import Path
import time
import numpy as np
from openwakeword.model import Model

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'models/wake'
model=Model(wakeword_models=[str(path/'hey_jarvis_v0.1.onnx')],inference_framework='onnx',
    melspec_model_path=str(path/'melspectrogram.onnx'),embedding_model_path=str(path/'embedding_model.onnx'))
rng=np.random.default_rng(52)
rows=[]
for kind in ('silence','low_level_noise'):
    model.reset(); maximum=0.; started=time.perf_counter()
    for _ in range(125):
        audio=np.zeros(1280,dtype=np.int16) if kind=='silence' else rng.integers(-100,101,1280,dtype=np.int16)
        result=model.predict(audio)
        maximum=max(maximum,max(float(v) for v in result.values()))
    rows.append({'kind':kind,'seconds_audio':10,'seconds_compute':round(time.perf_counter()-started,3),
        'maximum_score':maximum,'activation_at_0_5':maximum>=0.5})
report={'model':'hey_jarvis_v0.1.onnx','engine':'ONNX Runtime','synthetic_trials':rows,
    'owner_positive_trials':0,'household_false_activation_trial':'not performed',
    'license':'Code Apache-2.0; pretrained wake models CC-BY-NC-SA-4.0; personal noncommercial use only'}
(ROOT/'docs/reports/wake_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
