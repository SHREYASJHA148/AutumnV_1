import asyncio
import json
import time

import pytest

from autumn.brain.contracts import BrainError
from autumn.brain.transport import LoopbackTransport


def run_server(response, operation, *, delayed=False):
    async def trial():
        connections = []
        tasks = []
        async def serve(reader,writer):
            tasks.append(asyncio.current_task())
            try:
                header = await reader.readuntil(b"\r\n\r\n")
                connections.append(header.split(b"\r\n")[0])
                if delayed:
                    await asyncio.sleep(10)
                writer.write(response)
                await writer.drain()
            finally:
                writer.close()
        server = await asyncio.start_server(serve,"127.0.0.1",0)
        try:
            return await operation(LoopbackTransport(server.sockets[0].getsockname()[1]),connections)
        finally:
            server.close()
            await server.wait_closed()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
    return asyncio.run(trial())


def test_chunked_stream_framing_and_proxy_bypass(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY","http://127.0.0.1:1")
    packet=json.dumps({"message":{"content":"fixed"},"done":True}).encode()+b"\n"
    response=b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"+f"{len(packet):x}\r\n".encode()+packet+b"\r\n0\r\n\r\n"
    async def check(transport,connections):
        result=await transport.request("/api/chat",{},time.monotonic()+2,lambda:True,streaming=True)
        assert result[0]["done"] and connections==[b"POST /api/chat HTTP/1.1"]
    run_server(response,check)


def test_remote_redirect_not_followed():
    async def check(transport,connections):
        with pytest.raises(BrainError) as error:
            await transport.request("/api/tags",None,time.monotonic()+2,lambda:True)
        assert error.value.code=="RUNTIME_ERROR" and len(connections)==1
    run_server(b"HTTP/1.1 302 Found\r\nLocation: https://remote.invalid/\r\n\r\n",check)


@pytest.mark.parametrize("cancel",[True,False])
def test_cancel_and_deadline_close_a_stalled_connection(cancel):
    async def check(transport,connections):
        started=time.monotonic()
        with pytest.raises(BrainError) as error:
            await transport.request("/api/tags",None,started+(1 if cancel else 0.12),
                lambda:not cancel or time.monotonic()-started<0.10)
        assert error.value.code==("CANCELLED" if cancel else "TIMEOUT")
        assert time.monotonic()-started<0.5
    run_server(b"",check,delayed=True)


def test_oversized_body_is_rejected_without_reading_it():
    async def check(transport,connections):
        with pytest.raises(BrainError) as error:
            await transport.request("/api/tags",None,time.monotonic()+2,lambda:True)
        assert error.value.code=="RESPONSE_LIMIT"
    run_server(b"HTTP/1.1 200 OK\r\nContent-Length: 9999999\r\n\r\n",check)
