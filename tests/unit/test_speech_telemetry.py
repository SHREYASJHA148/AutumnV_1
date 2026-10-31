import queue
import threading
from types import SimpleNamespace

from autumn.speech.workers import speech_main


def test_full_telemetry_queue_does_not_kill_idle_speech_worker(tmp_path):
    replies = queue.Queue(maxsize=1)
    stopping = threading.Event()
    thread = threading.Thread(target=speech_main,
        args=(queue.Queue(), replies, SimpleNamespace(value=0), stopping, str(tmp_path), False),
        kwargs={"role": "recognition"}, daemon=True)
    thread.start()
    try:
        assert replies.get(timeout=2)["kind"] == "heartbeat"
        # Leave one heartbeat queued, then let several more become due without consuming them.
        stopping.wait(1.1)
        assert thread.is_alive() and replies.qsize() == 1
    finally:
        stopping.set()
        thread.join(timeout=2)
    assert not thread.is_alive()
