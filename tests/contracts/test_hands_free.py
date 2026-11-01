"""Hands-free controller tests with fake audio; never opens a microphone."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('voice_fixtures',Path(__file__).with_name('test_voice.py'))
fixtures=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def listening():
    vm=fixtures.make_vm()
    vm.voice.setHandsFree(True)
    vm.voice.next_listen=0
    vm.poll()
    assert vm.voice.recording and vm.voice.service.sent[-1][2]['endpoint']
    return vm


def phrase(vm,text):
    operation=fixtures.captured(vm)
    vm.voice.service.messages=[{'kind':'recognized','operation_id':str(operation),'result':{'accepted':True,'text':text}}]
    vm.poll()


def test_addressed_command_uses_restricted_background_origin():
    vm=listening()
    try:
        phrase(vm,'Autumn, open Spotify')
        assert vm.supervisor.jobs[-1].text=='open Spotify'
        assert vm.supervisor.jobs[-1].request.origin=='wake_voice'
    finally:
        vm.shutdown()


def test_unaddressed_audio_is_discarded_without_transcript_or_dispatch():
    vm=listening()
    try:
        phrase(vm,'This is a private conversation')
        assert not vm.voice.transcript and vm.session.active is None
        assert not any(j.kind=='execute' for j in vm.supervisor.jobs)
        assert all('private conversation' not in row['text'] for row in vm.conversation)
        assert vm.voice.hands_free
    finally:
        vm.shutdown()


def test_stop_disarms_and_poll_does_not_restart_the_microphone():
    vm=listening()
    try:
        vm.stop()
        sent=len(vm.voice.service.sent)
        vm.voice.next_listen=0
        vm.poll()
        assert not vm.voice.hands_free and not vm.voice.recording
        assert len(vm.voice.service.sent)==sent
    finally:
        vm.shutdown()


def test_spoken_stop_pauses_hands_free_and_never_goes_to_the_model():
    vm=listening()
    try:
        phrase(vm,'Autumn stop listening')
        assert not vm.voice.hands_free and not any(j.kind=='execute' for j in vm.supervisor.jobs)
    finally:
        vm.shutdown()


def test_device_loss_pauses_instead_of_reopening_forever():
    vm=listening()
    try:
        vm.voice.service.messages=[{'kind':'capture_error','operation_id':str(vm.voice.capture_id),'code':'DEVICE_UNAVAILABLE'}]
        vm.poll()
        assert not vm.voice.hands_free and not vm.voice.enabled
    finally:
        vm.shutdown()


def test_silence_retries_without_dispatch():
    vm=listening()
    try:
        vm.voice.service.messages=[{'kind':'capture_error','operation_id':str(vm.voice.capture_id),'code':'SILENT_CAPTURE'}]
        vm.poll()
        assert vm.voice.hands_free and vm.session.active is None
        vm.voice.next_listen=0
        vm.poll()
        assert vm.voice.recording
    finally:
        vm.shutdown()


def test_reply_playback_and_its_tail_pause_hands_free_capture():
    vm=listening()
    try:
        vm.voice.recording=False
        vm.voice.capture_id=None
        vm.voice.speak('Public test reply')
        vm.voice.next_listen=0
        vm.poll()
        assert vm.voice.playing and not vm.voice.recording
        vm.voice.service.messages=[{'kind':'played','operation_id':str(vm.voice.playback_id)}]
        vm.poll()
        assert not vm.voice.recording and vm.voice.tail_until>0
        vm.voice.tail_until=0
        vm.voice.next_listen=0
        vm.poll()
        assert vm.voice.hands_free and vm.voice.recording
    finally:
        vm.shutdown()
