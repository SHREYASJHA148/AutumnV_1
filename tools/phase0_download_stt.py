"""Pin and checksum local recognition weights, with bounded downloads."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parents[1]


def read_json(url):
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model', choices=['base.en', 'small.en'])
    parser.add_argument('--max-seconds', type=int, default=900)
    args = parser.parse_args()
    repo = 'ggerganov/whisper.cpp'
    revision = read_json(f'https://huggingface.co/api/models/{repo}')['sha']
    entries = read_json(f'https://huggingface.co/api/models/{repo}/tree/{revision}')
    name = f'ggml-{args.model}.bin'
    item = next(i for i in entries if i['path'] == name)
    expected = item['lfs']['oid']
    destination = ROOT / 'models/stt'
    destination.mkdir(parents=True, exist_ok=True)
    partial = destination / (name + '.partial')
    url = f'https://huggingface.co/{repo}/resolve/{revision}/{name}?download=true&phase0={int(time.time())}'
    started = time.monotonic()
    digest = hashlib.sha256()
    request=Request(url,headers={'Range':f'bytes=0-{item["size"]-1}','Accept-Encoding':'identity'})
    with urlopen(request, timeout=30) as response, partial.open('wb') as stream:
        content_range=response.headers.get('Content-Range','')
        if response.status==206 and not content_range.startswith('bytes 0-'):
            raise ValueError('Unexpected partial response start offset')
        length=response.headers.get('Content-Length')
        if length and int(length)!=item['size']:
            raise ValueError('Response length is not the complete artifact')
        while chunk := response.read(1024 * 1024):
            if time.monotonic() - started > min(args.max_seconds, 3600):
                raise TimeoutError('Recognition weight download reached the approved limit')
            stream.write(chunk)
            digest.update(chunk)
    if digest.hexdigest() != expected or partial.stat().st_size != item['size']:
        raise ValueError('Recognition artifact checksum/size mismatch')
    target = destination / name
    partial.replace(target)
    report = {'name': name, 'revision': revision, 'sha256': expected, 'bytes': target.stat().st_size, 'url': url}
    (ROOT / f'docs/reports/stt_{args.model}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Verified {args.model} recognition weights; no audio captured.')


if __name__ == '__main__':
    main()
