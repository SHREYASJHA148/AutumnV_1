"""Readiness/import and native-worker experiments; no microphone recording."""
from __future__ import annotations

import ctypes
import importlib
import importlib.metadata as metadata
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REPORT_NAME = os.environ.get('AUTUMN_COMPONENT_REPORT', 'component_probe.json')
if Path(REPORT_NAME).name != REPORT_NAME or not REPORT_NAME.endswith('.json'):
    raise ValueError('Component report must remain a JSON filename inside project reports')
REPORT = ROOT / 'docs' / 'reports' / REPORT_NAME
MODULES = {
    'PySide6-Essentials': 'PySide6', 'pydantic': 'pydantic', 'sounddevice': 'sounddevice',
    'onnxruntime': 'onnxruntime', 'pywhispercpp': 'pywhispercpp.model',
    'piper-tts': 'piper', 'openwakeword': 'openwakeword', 'pywin32': 'win32api',
    'pycaw': 'pycaw.pycaw', 'pywinauto': 'pywinauto', 'psutil': 'psutil',
}


def audio_worker(connection) -> None:
    """Set current volume to itself, verify, then await a supervised kill."""
    import comtypes
    from pycaw.pycaw import AudioUtilities
    comtypes.CoInitialize()
    try:
        endpoint = AudioUtilities.GetSpeakers().EndpointVolume
        before = endpoint.GetMasterVolumeLevelScalar()
        endpoint.SetMasterVolumeLevelScalar(before, None)
        after = endpoint.GetMasterVolumeLevelScalar()
        connection.send({'readback_matches': abs(before - after) < 0.001})
        time.sleep(55)
    except Exception as exc:
        connection.send({'error_type': type(exc).__name__, 'message': str(exc)[:200]})
    finally:
        comtypes.CoUninitialize()


def run() -> None:
    report: dict = {'python_version': sys.version.split()[0], 'imports': {}, 'licenses': []}
    for distribution, module in MODULES.items():
        try:
            importlib.import_module(module)
            report['imports'][distribution] = {'status': 'pass', 'version': metadata.version(distribution)}
        except Exception as exc:
            report['imports'][distribution] = {'status': 'fail', 'error_type': type(exc).__name__, 'message': str(exc)[:300]}
    for distribution in metadata.distributions():
        info = distribution.metadata
        report['licenses'].append({
            'name': info['Name'], 'version': info['Version'],
            'declared_license': info.get('License-Expression') or info.get('License', '')[:160],
            'classifiers': [x for x in info.get_all('Classifier', []) if x.startswith('License ::')],
        })
    try:
        import sounddevice as sd
        report['audio_devices'] = [
            {'id': i, 'name': d['name'], 'input_channels': d['max_input_channels'],
             'output_channels': d['max_output_channels'], 'sample_rate': d['default_samplerate']}
            for i, d in enumerate(sd.query_devices())
        ]
        report['audio_default_ids'] = list(sd.default.device)
    except Exception as exc:
        report['audio_error'] = type(exc).__name__
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    # CTRL+ALT+F12: registration only. No key hook or input recording.
    hotkey = bool(user32.RegisterHotKey(None, 901, 0x0002 | 0x0001 | 0x4000, 0x7B))
    report['temporary_hotkey_registration'] = hotkey
    if hotkey:
        user32.UnregisterHotKey(None, 901)
    attempts = []
    for _ in range(2):
        parent, child = mp.Pipe(duplex=False)
        process = mp.Process(target=audio_worker, args=(child,))
        process.start()
        child.close()
        try:
            outcome = parent.recv() if parent.poll(15) else {'error': 'worker timeout'}
        finally:
            if process.is_alive():
                process.terminate()
            process.join(5)
            parent.close()
        attempts.append({**outcome, 'owned_worker_stopped': not process.is_alive()})
    report['volume_worker_restart_trials'] = attempts
    REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
    failures = [name for name, result in report['imports'].items() if result['status'] == 'fail']
    print(json.dumps({'import_failures': failures, 'hotkey_registered': hotkey, 'worker_trials': attempts}))


if __name__ == '__main__':
    mp.freeze_support()
    run()
