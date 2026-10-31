"""Injectable source boundary. Phase 1 never opens an audio device."""
from collections.abc import Iterator
from typing import Protocol


class AudioSource(Protocol):
    def frames(self) -> Iterator[bytes]: ...
    def close(self) -> None: ...


class FakeAudioSource:
    def __init__(self, chunks: tuple[bytes, ...] = ()) -> None:
        self.chunks = chunks
        self.closed = False

    def frames(self) -> Iterator[bytes]:
        for chunk in self.chunks:
            if self.closed:
                return
            yield chunk

    def close(self) -> None:
        self.closed = True
