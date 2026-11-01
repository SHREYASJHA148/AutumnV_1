import numpy as np
import pytest

from autumn.audio.endpoint import SpeechEndpoint
from autumn.speech.synthesis import action_reply


class Detector:
    def __init__(self):
        self.frames=0
    def is_speech(self,pcm,rate):
        assert len(pcm)==960 and rate==16000
        self.frames+=1
        return np.max(np.abs(np.frombuffer(pcm,dtype='<i2')))>300


def test_continuous_frames_detect_a_short_pause_and_preserve_word_edges():
    detector=Detector()
    endpoint=SpeechEndpoint(detector)
    audio=np.concatenate((np.zeros(16000),np.full(16000,.1),np.zeros(8000))).astype(np.float32)
    for chunk in np.array_split(audio,37):
        endpoint.feed(chunk)
    assert detector.frames==len(audio)//480
    assert endpoint.heard_speech and endpoint.finished
    start,end=endpoint.bounds(16000,len(audio))
    assert start<=16000 and end>=32000
    assert end-start<len(audio)


def test_endpoint_does_not_cut_a_pause_shorter_than_the_window():
    endpoint=SpeechEndpoint(Detector())
    endpoint.feed(np.full(16000,.1,dtype=np.float32))
    endpoint.feed(np.zeros(6400,dtype=np.float32))
    assert not endpoint.finished
    endpoint.feed(np.zeros(1600,dtype=np.float32))
    assert endpoint.finished


def test_silence_is_never_treated_as_a_command_and_pending_audio_is_discarded():
    endpoint=SpeechEndpoint(Detector())
    endpoint.feed(np.zeros(16001,dtype=np.float32))
    assert not endpoint.heard_speech and not endpoint.finished
    pending=endpoint.pending
    endpoint.discard()
    assert not pending.any() and endpoint.pending.size==0
    with pytest.raises(ValueError):
        endpoint.feed(np.array([float('nan')],dtype=np.float32))


def test_short_spoken_acknowledgments_keep_uncertainty_and_failure_details():
    assert action_reply('Full verification detail','app.open','succeeded')=='App started.'
    assert 'not verified' in action_reply('Long handoff description','app.open','unverified')
    assert action_reply('Exact recovery instruction','app.open','failed')=='Exact recovery instruction'
    assert action_reply('Partial delivery details','text.type','partial')=='Partial delivery details'


def test_longer_pause_preserves_a_natural_gap_until_the_selected_window():
    endpoint=SpeechEndpoint(Detector(),silence_ms=800)
    endpoint.feed(np.full(16000,.1,dtype=np.float32))
    endpoint.feed(np.zeros(11200,dtype=np.float32))
    assert not endpoint.finished
    endpoint.feed(np.zeros(2400,dtype=np.float32))
    assert endpoint.finished


def test_response_pause_cannot_remove_the_silence_safeguard():
    with pytest.raises(ValueError):
        SpeechEndpoint(silence_ms=0)
