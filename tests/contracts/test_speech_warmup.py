import queue
import threading
from types import SimpleNamespace

import numpy as np
import pytest
import sounddevice

from autumn.speech import recognition, synthesis
from autumn.speech.workers import speech_main


@pytest.mark.parametrize('role',['recognition','playback'])
def test_priming_only_loads_components_without_opening_audio(monkeypatch,tmp_path,role):
    calls=[]
    audio=np.ones(160,dtype=np.float32)
    class Recognizer:
        def prepare(self,*args):
            calls.append('recognition')
    class Synthesizer:
        def render(self,*args):
            calls.append('playback')
            return audio,16000
    def no_device(*args,**kwargs):
        raise AssertionError('Warm-up must never open an audio device')
    monkeypatch.setattr(recognition,'Recognizer',Recognizer)
    monkeypatch.setattr(synthesis,'Synthesizer',Synthesizer)
    monkeypatch.setattr(sounddevice,'InputStream',no_device)
    monkeypatch.setattr(sounddevice,'OutputStream',no_device)
    commands,replies=queue.Queue(),queue.Queue()
    stopping=threading.Event()
    thread=threading.Thread(target=speech_main,args=(commands,replies,SimpleNamespace(value=0),stopping,str(tmp_path),False),kwargs={'role':role},daemon=True)
    thread.start()
    try:
        commands.put({'kind':'warm','generation':0})
        for _ in range(4):
            event=replies.get(timeout=2)
            if event['kind']=='speech_warmed':
                break
        else:
            raise AssertionError('No warm-up acknowledgment')
        assert calls==[role]
        if role=='playback':
            assert not audio.any()
        assert not list(tmp_path.iterdir())
    finally:
        stopping.set()
        thread.join(timeout=2)
        assert not thread.is_alive()
