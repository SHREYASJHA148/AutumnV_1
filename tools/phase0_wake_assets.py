"""Download only pinned-release ONNX wake assets, never microphone audio."""
import hashlib
import json
from pathlib import Path
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
with urlopen('https://api.github.com/repos/dscripka/openWakeWord/releases/tags/v0.5.1',timeout=30) as response:
    release=json.load(response)
output=ROOT/'models/wake'; output.mkdir(parents=True,exist_ok=True)
records=[]
for name in ('melspectrogram.onnx','embedding_model.onnx','hey_jarvis_v0.1.onnx'):
    asset=next(a for a in release['assets'] if a['name']==name)
    target=output/name; started=time.monotonic(); digest=hashlib.sha256()
    with urlopen(asset['browser_download_url'],timeout=30) as response,target.with_suffix('.partial').open('wb') as stream:
        while chunk:=response.read(1024*1024):
            if time.monotonic()-started>900: raise TimeoutError('Wake asset download time limit')
            digest.update(chunk); stream.write(chunk)
    partial=target.with_suffix('.partial')
    if partial.stat().st_size!=asset['size']: raise ValueError('Asset size mismatch')
    expected=asset.get('digest')
    if expected and expected!='sha256:'+digest.hexdigest(): raise ValueError('Release digest mismatch')
    partial.replace(target)
    records.append({'name':name,'release':'v0.5.1','asset_id':asset['id'],'bytes':target.stat().st_size,
        'sha256':digest.hexdigest(),'upstream_digest':expected,'url':asset['browser_download_url']})
(ROOT/'docs/reports/wake_artifacts.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('Three wake assets downloaded; local digests recorded; upstream digests checked when provided.')
