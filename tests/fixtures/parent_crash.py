"""Disposable parent; no desktop actions or audio hardware are used."""
import json
import os
import sys
import time
from pathlib import Path

from autumn.controller.worker import Supervisor

if __name__ == '__main__':
    root = Path(sys.argv[1])
    supervisor = Supervisor(root)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if any(e['kind'] == 'ready' for e in supervisor.poll()):
            (root / 'ready.json').write_text(json.dumps({'pid':supervisor.process.pid}))
            while not (root / 'crash-now').exists():
                supervisor.poll()
                time.sleep(.02)
            os._exit(7)
        time.sleep(.02)
    supervisor.shutdown()
    raise SystemExit(1)
