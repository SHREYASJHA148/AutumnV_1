"""Fetch the selected Piper candidate with upstream revision and LFS hash checks."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def get_json(url: str):
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def main():
    repo = 'rhasspy/piper-voices'
    revision = get_json(f'https://huggingface.co/api/models/{repo}')['sha']
    directory = 'en/en_US/lessac/medium'
    files = get_json(f'https://huggingface.co/api/models/{repo}/tree/{revision}/{directory}')
    destination = ROOT / 'models/tts'
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for item in files:
        name = item['path'].rsplit('/', 1)[-1]
        if name not in ('en_US-lessac-medium.onnx', 'en_US-lessac-medium.onnx.json', 'MODEL_CARD'):
            continue
        output = destination / name
        partial = output.with_suffix(output.suffix + '.partial')
        digest = hashlib.sha256()
        started = time.monotonic()
        url = f'https://huggingface.co/{repo}/resolve/{revision}/{item["path"]}'
        with urlopen(url, timeout=30) as response, partial.open('wb') as stream:
            while chunk := response.read(1024 * 1024):
                if time.monotonic() - started > 900:
                    raise TimeoutError('Download exceeded 15 minutes')
                digest.update(chunk)
                stream.write(chunk)
        expected = item.get('lfs', {}).get('oid')
        actual = digest.hexdigest()
        if expected and expected != actual:
            raise ValueError('Upstream LFS checksum mismatch')
        if partial.stat().st_size != item['size']:
            raise ValueError('Upstream size mismatch')
        partial.replace(output)
        records.append({'name': name, 'bytes': output.stat().st_size, 'sha256': actual,
                        'upstream_lfs_sha256': expected, 'revision': revision, 'url': url})
    (ROOT / 'docs/reports/voice_artifacts.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(f'Verified {len(records)} voice artifacts; no playback or recording performed.')


if __name__ == '__main__':
    main()
