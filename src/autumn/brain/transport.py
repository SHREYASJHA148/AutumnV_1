"""Bounded cancellable HTTP over literal loopback; ignores proxies and redirects."""
from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable

from autumn.brain.contracts import BrainError

PATHS = {"/api/tags", "/api/show", "/api/chat", "/api/ps"}


class LoopbackTransport:
    def __init__(self, port: int = 11434):
        if not 1 <= port <= 65535:
            raise ValueError("Invalid loopback port")
        self.port = port

    async def request(self, path: str, body: dict | None, deadline: float,
                      checkpoint: Callable[[], bool], *, streaming: bool = False,
                      on_packet: Callable[[dict], None] | None = None):
        if path not in PATHS:
            raise BrainError("ENDPOINT_DENIED")
        writer = None

        async def wait(operation):
            task = asyncio.ensure_future(operation)
            try:
                while not task.done():
                    if not checkpoint():
                        raise BrainError("CANCELLED")
                    if time.monotonic() >= deadline:
                        raise BrainError("TIMEOUT")
                    await asyncio.wait({task}, timeout=min(0.05, max(0, deadline - time.monotonic())))
                return task.result()
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)

        try:
            reader, writer = await wait(asyncio.open_connection("127.0.0.1", self.port, limit=16384))
            payload = b"" if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
            if len(payload) > 64_000:
                raise BrainError("CONTEXT_LIMIT")
            method = "GET" if body is None else "POST"
            writer.write((f"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
                          "Content-Type: application/json\r\nConnection: close\r\n"
                          f"Content-Length: {len(payload)}\r\n\r\n").encode("ascii") + payload)
            await wait(writer.drain())
            headers = await wait(reader.readuntil(b"\r\n\r\n"))
            if len(headers) > 8192:
                raise BrainError("RESPONSE_LIMIT")
            lines = headers.decode("iso-8859-1").split("\r\n")
            if lines[0].split()[1] != "200":
                raise BrainError("RUNTIME_ERROR")
            fields = {line.split(":",1)[0].strip().lower():line.split(":",1)[1].strip().lower()
                      for line in lines[1:] if ":" in line}
            chunked = fields.get("transfer-encoding") == "chunked"
            length = int(fields["content-length"]) if "content-length" in fields else None
            limit = 512_000 if not streaming else 96_000
            if length is not None and (length < 0 or length > limit):
                raise BrainError("RESPONSE_LIMIT")
            received = 0
            pending = bytearray()
            objects = []
            remaining = length
            while True:
                if chunked:
                    line = await wait(reader.readline())
                    if len(line) > 80:
                        raise BrainError("RESPONSE_LIMIT")
                    size = int(line.split(b";",1)[0], 16)
                    if size == 0:
                        break
                    if size < 0 or size + received > limit:
                        raise BrainError("RESPONSE_LIMIT")
                    data = await wait(reader.readexactly(size))
                    if await wait(reader.readexactly(2)) != b"\r\n":
                        raise BrainError("MALFORMED_RESPONSE")
                else:
                    if remaining == 0:
                        break
                    data = await wait(reader.read(min(4096, remaining) if remaining is not None else 4096))
                    if not data:
                        if remaining not in (None, 0):
                            raise BrainError("MALFORMED_RESPONSE")
                        break
                    if remaining is not None:
                        remaining -= len(data)
                received += len(data)
                if received > limit:
                    raise BrainError("RESPONSE_LIMIT")
                pending.extend(data)
                if streaming:
                    while b"\n" in pending:
                        line, _, rest = pending.partition(b"\n")
                        pending = bytearray(rest)
                        if line.strip():
                            packet = json.loads(line)
                            objects.append(packet)
                            if on_packet is not None:
                                on_packet(packet)
                    if len(pending) > 16384 or len(objects) > 600:
                        raise BrainError("RESPONSE_LIMIT")
            if streaming:
                if pending.strip():
                    packet = json.loads(pending)
                    objects.append(packet)
                    if on_packet is not None:
                        on_packet(packet)
                return objects
            return json.loads(pending)
        except BrainError:
            raise
        except (OSError, ValueError, KeyError, IndexError, asyncio.IncompleteReadError,
                asyncio.LimitOverrunError):
            raise BrainError("RUNTIME_UNAVAILABLE") from None
        finally:
            if writer is not None:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), timeout=0.2)
                except (OSError, TimeoutError):
                    pass
