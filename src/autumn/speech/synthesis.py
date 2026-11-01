"""Local Piper with bounded replies; no dynamic speech/audio written to disk."""

import re

import numpy as np

from autumn.speech.assets import Assets, native_path


def short_reply(text):
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())[:2]
    return " ".join(" ".join(sentences).split()[:36])[:350]


def action_reply(message, skill='', status=''):
    """Keep full verification detail on screen; speak brief, truthful acknowledgments."""
    if skill in {'app.open','folder.open','website.open'}:
        if status == 'succeeded':
            return 'App started.' if skill == 'app.open' else 'Opened.'
        if status == 'unverified':
            return 'Opening requested; not verified.'
    if status == 'succeeded':
        return {'audio.set_volume':'Volume updated.','audio.set_mute':'Audio updated.',
                'screen.capture':'Screenshot saved.','media.control':'Media updated.'}.get(skill,message)
    if status == 'unverified' and skill == 'media.control':
        return 'Media request sent; not verified.'
    return message


class Synthesizer:
    def __init__(self):
        self.assets = Assets()
        self.voice = None
        self.loaded = None

    def render(self, text, root, volume, rate, checkpoint):
        from piper import PiperVoice, SynthesisConfig
        from piper.phonemize_espeak import ESPEAK_DATA_DIR

        path = self.assets.get("voice", root)
        self.assets.get("voice_config", root)
        if self.loaded != str(path):
            if not all((ESPEAK_DATA_DIR / name).is_file() for name in ("phontab", "phondata", "phonindex")):
                raise ValueError("Pronunciation data missing")
            self.voice = PiperVoice.load(native_path(path), espeak_data_dir=native_path(ESPEAK_DATA_DIR))
            self.loaded = str(path)
        limit = 15 * 22050
        chunks = []
        used = 0
        for chunk in self.voice.synthesize(
            short_reply(text), SynthesisConfig(volume=volume, length_scale=1 / rate)
        ):
            if not checkpoint():
                raise InterruptedError()
            data = np.asarray(chunk.audio_float_array, dtype=np.float32).reshape(-1)
            data = data[: max(0, limit - used)]
            if len(data):
                chunks.append(data.copy())
            used += len(data)
            if used >= limit:
                break
        if not chunks:
            raise ValueError("Empty speech output")
        return np.concatenate(chunks), 22050
