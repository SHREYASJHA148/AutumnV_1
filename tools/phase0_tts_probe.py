"""Synthesize fixed public test phrases; never capture microphone audio."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import time
import wave

from piper import PiperVoice

ROOT = Path(__file__).resolve().parents[1]
PHRASES = [
    'Hello. I am Autumn.', 'Your local assistant is ready.',
    'I can open a registered application.', 'Which folder did you mean?',
    'The microphone is off.', 'Your screenshot has been saved.',
    'I could not verify that action.', 'Please confirm the text and destination.',
    'The current task has been cancelled.', 'You are in control.',
]


def main():
    model = ROOT / 'models/tts/en_US-lessac-medium.onnx'
    output = ROOT / '.cache/voice-tests'
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    voice = PiperVoice.load(str(model))
    rows = []
    for index, phrase in enumerate(PHRASES):
        target = output / f'piper-{index:02}.wav'
        before = time.perf_counter()
        with wave.open(str(target), 'wb') as stream:
            voice.synthesize_wav(phrase, stream)
        with wave.open(str(target), 'rb') as stream:
            frames = stream.getnframes()
            duration = frames / stream.getframerate()
        rows.append({'case': index + 1, 'seconds_audio': round(duration, 3),
                     'seconds_synthesis': round(time.perf_counter() - before, 3), 'frames': frames})
    result = {'voice': 'en_US-lessac-medium', 'python_version': sys.version.split()[0],
              'phrases_synthesized': len(rows),
              'total_seconds': round(time.perf_counter() - started, 3),
              'playback_tested': False, 'owner_quality_rating': 'not evaluated', 'rows': rows}
    report_name = os.environ.get('AUTUMN_TTS_REPORT', 'piper_tts.json')
    if Path(report_name).name != report_name or not report_name.endswith('.json'):
        raise ValueError('TTS report must remain a JSON filename inside project reports')
    (ROOT / 'docs/reports' / report_name).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f'Piper synthesized {len(rows)} valid WAV files; playback and quality not evaluated.')


if __name__ == '__main__':
    main()
