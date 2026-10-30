"""Pull only the approved baseline into Ollama's authorized model cache."""
import json
import argparse
from pathlib import Path
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--max-seconds', type=int, default=900)
parser.add_argument('--model', choices=['qwen3:1.7b', 'qwen3.5:2b'], default='qwen3:1.7b')
args = parser.parse_args()
if not 1 <= args.max_seconds <= 3600:
    raise ValueError('Download time limit must be within the approved hour')
started = time.monotonic()
request = Request('http://127.0.0.1:11434/api/pull',
                  data=json.dumps({'model': args.model, 'stream': True}).encode(),
                  headers={'Content-Type': 'application/json'})
last_bucket = -1
with urlopen(request, timeout=60) as response:
    for line in response:
        if time.monotonic() - started > args.max_seconds:
            raise TimeoutError('Model pull reached the approved time limit')
        event = json.loads(line)
        if 'error' in event:
            raise RuntimeError(event['error'])
        if event.get('total'):
            bucket = int(10 * event.get('completed', 0) / event['total'])
            if bucket != last_bucket:
                print(f'{args.model} download: {bucket * 10}%', flush=True)
                last_bucket = bucket
        elif event.get('status') == 'success':
            print('Baseline download verified by Ollama.', flush=True)
with urlopen('http://127.0.0.1:11434/api/tags', timeout=5) as response:
    tags = json.load(response)
model = next(m for m in tags['models'] if m['name'] == args.model)
model['pull_elapsed_seconds'] = round(time.monotonic() - started, 2)
report_name = 'baseline_model.json' if args.model == 'qwen3:1.7b' else 'candidate_model.json'
(ROOT / 'docs/reports' / report_name).write_text(json.dumps(model, indent=2), encoding='utf-8')
