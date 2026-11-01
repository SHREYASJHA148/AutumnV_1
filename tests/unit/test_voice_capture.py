import queue
import threading
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
import sounddevice

from autumn.audio import devices
from autumn.speech.workers import speech_main
from autumn.winworker import cache


class MemoryInput:
    instances = []

    def __init__(self, **options):
        self.callback = options["callback"]
        self.active = False
        self.closed = False
        self.instances.append(self)

    def start(self):
        self.active = True
        self.callback(np.ones((960, 1), dtype=np.float32) * 0.05, 960, None, None)

    def abort(self):
        self.active = False

    def close(self):
        self.closed = True


@pytest.mark.parametrize("outcome", ["finish", "cancel", "default_changed", "unavailable", "released_before_start"])
def test_injected_capture_closes_device_and_never_saves_audio(monkeypatch, tmp_path, outcome):
    MemoryInput.instances.clear()
    monkeypatch.setattr(sounddevice, "InputStream", MemoryInput)
    monkeypatch.setattr(cache, "configure", lambda root: None)
    monkeypatch.setattr(devices, "resolve_device", lambda token, kind: {"rate": 16000, "index": 0})
    calls = []

    def endpoint(kind):
        calls.append(kind)
        return "changed" if outcome == "default_changed" and len(calls) > 1 else "initial"

    monkeypatch.setattr(devices, "default_endpoint", endpoint)
    if outcome == "unavailable":
        def missing(**options):
            raise OSError("Injected unavailable device")
        monkeypatch.setattr(sounddevice, "InputStream", missing)
    commands, replies = queue.Queue(), queue.Queue()
    generation = SimpleNamespace(value=0)
    stopping = threading.Event()
    capture_gate = SimpleNamespace(value=outcome != "released_before_start")
    thread = threading.Thread(target=speech_main, args=(commands, replies, generation, stopping, str(tmp_path), False), kwargs={"role": "capture", "capture_gate": capture_gate}, daemon=True)
    thread.start()
    operation = uuid4()
    commands.put({"kind": "capture", "generation": 0, "operation_id": operation})
    seen = []
    try:
        while True:
            event = replies.get(timeout=2)
            seen.append(event)
            if event["kind"] == "recording":
                if outcome == "finish":
                    commands.put({"kind": "finish_capture", "generation": 0, "operation_id": operation})
                elif outcome == "cancel":
                    generation.value = 1
            if event["kind"] in {"captured", "capture_error", "speech_error"}:
                break
        if outcome == "finish":
            assert event["kind"] == "captured" and len(event["pcm"]) == 960 * 4
        else:
            assert not any(e["kind"] == "captured" for e in seen)
            assert event["kind"] in {"capture_error", "speech_error"}
    finally:
        stopping.set()
        thread.join(timeout=2)
    assert not thread.is_alive()
    assert all(instance.closed for instance in MemoryInput.instances)
    if outcome == "released_before_start":
        assert not MemoryInput.instances
    assert not list(tmp_path.iterdir())


def test_endpoint_finishes_speech_and_removes_surrounding_silence(monkeypatch,tmp_path):
    from autumn.audio import endpoint
    original=endpoint.SpeechEndpoint
    class Detector:
        def is_speech(self,pcm,rate):
            return bool(np.max(np.abs(np.frombuffer(pcm,dtype='<i2')))>300)
    monkeypatch.setattr(endpoint,'SpeechEndpoint',lambda **kwargs:original(Detector(),**kwargs))
    frames=np.concatenate((np.zeros(16000),np.full(16000,.1),np.zeros(16000))).astype(np.float32)
    instances=[]
    class Stream:
        def __init__(self,**options):
            self.callback=options['callback']
            self.started=False
            self.closed=False
            self.cursor=0
            instances.append(self)
        def start(self):
            self.started=True
        @property
        def active(self):
            if self.started and self.cursor<len(frames):
                chunk=frames[self.cursor:self.cursor+800]
                self.cursor+=len(chunk)
                self.callback(chunk.reshape(-1,1),len(chunk),None,None)
            return self.started
        def abort(self):
            self.started=False
        def close(self):
            self.closed=True
    monkeypatch.setattr(sounddevice,'InputStream',Stream)
    monkeypatch.setattr(cache,'configure',lambda root:None)
    monkeypatch.setattr(devices,'resolve_device',lambda *args:{'rate':16000,'index':0})
    monkeypatch.setattr(devices,'default_endpoint',lambda kind:'fixed')
    commands,replies=queue.Queue(),queue.Queue()
    stopping=threading.Event()
    thread=threading.Thread(target=speech_main,args=(commands,replies,SimpleNamespace(value=0),stopping,str(tmp_path),False),kwargs={'role':'capture','capture_gate':SimpleNamespace(value=True)},daemon=True)
    thread.start()
    try:
        commands.put({'kind':'capture','generation':0,'operation_id':uuid4(),'endpoint':True})
        for _ in range(100):
            event=replies.get(timeout=3)
            if event['kind']=='captured':
                break
            assert event['kind'] not in {'capture_error','speech_error'}
        else:
            raise AssertionError('No endpoint result')
        assert .9*16000*4<=len(event['pcm'])<=1.5*16000*4
        assert all(s.closed for s in instances)
    finally:
        stopping.set()
        thread.join(timeout=2)
        assert not thread.is_alive()
