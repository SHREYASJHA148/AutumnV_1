"""Resume a verified-prefix download using bounded HTTP byte ranges; final SHA mandatory."""
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
revision=json.loads((ROOT/'docs/reports/stt_base.en.json').read_text())['revision']
with urlopen(f'https://huggingface.co/api/models/ggerganov/whisper.cpp/tree/{revision}',timeout=30) as response:
    item=next(x for x in json.load(response) if x['path']=='ggml-small.en.bin')
partial=ROOT/'models/stt/ggml-small.en.bin.partial'; total=item['size']
if partial.exists() and partial.stat().st_size:
    with partial.open('rb') as stream:
        if stream.read(4)!=b'lmgg':raise ValueError('Existing prefix has no GGML header')
started=time.monotonic(); failures=0; block=4*1024*1024; last=-1
while (partial.stat().st_size if partial.exists() else 0)<total:
    if time.monotonic()-started>1800:raise TimeoutError('Resumable download reached its bounded 30-minute run')
    position=partial.stat().st_size if partial.exists() else 0
    end=min(position+block-1,total-1)
    url=f'https://huggingface.co/ggerganov/whisper.cpp/resolve/{revision}/ggml-small.en.bin?download=true&range={position}-{end}&nonce={time.time_ns()}'
    request=Request(url,headers={'Range':f'bytes={position}-{end}','Accept-Encoding':'identity'})
    before=position
    try:
        with urlopen(request,timeout=30) as response:
            match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
            if response.status!=206 or not match or tuple(map(int,match.groups()))!=(position,end,total):
                raise ValueError('Range server did not return the exact requested span')
            with partial.open('ab') as stream:
                remaining=end-position+1
                while remaining:
                    chunk=response.read(min(65536,remaining))
                    if not chunk:raise EOFError('Range body ended early')
                    stream.write(chunk); remaining-=len(chunk)
        failures=0
    except Exception as exc:
        position=partial.stat().st_size if partial.exists() else 0
        if position==before:
            failures+=1; block=max(512*1024,block//2)
        else: failures=0
        print(f'Range transfer interrupted ({type(exc).__name__}); verified position {position}/{total}',flush=True)
        if failures>=3:raise RuntimeError('Three no-progress range attempts; stop and report') from exc
    bucket=int(partial.stat().st_size*10/total)
    if bucket!=last: print(f'Small English model: {bucket*10}%',flush=True);last=bucket
with partial.open('rb') as stream: actual=hashlib.file_digest(stream,'sha256').hexdigest()
if actual!=item['lfs']['oid'] or partial.stat().st_size!=total:raise ValueError('Final artifact integrity mismatch')
target=ROOT/'models/stt/ggml-small.en.bin';partial.replace(target)
report={'name':target.name,'revision':revision,'bytes':total,'sha256':actual,'method':'resumable exact HTTP byte ranges; final upstream LFS SHA256 verified'}
(ROOT/'docs/reports/stt_small.en.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Small English model integrity verified.',flush=True)
