import asyncio
import json
import sys
from pathlib import Path
import types

# Ensure project root on path and provide a dummy ``websockets`` module so
# the client can be imported without the real dependency.
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault("websockets", types.SimpleNamespace())


def test_env_uri_and_context_manager(monkeypatch):
    from Client.network import ws_client

    class DummyWebSocket:
        def __init__(self):
            self.sent = []
            self.closed = False

        async def send(self, data):
            self.sent.append(data)

        async def recv(self):
            return json.dumps({"status": "ok"})

        async def close(self):
            self.closed = True

    dummy_ws = DummyWebSocket()

    async def fake_connect(uri):
        assert uri == "ws://dummy"
        return dummy_ws

    monkeypatch.setenv("SERVER_URI", "ws://dummy")
    monkeypatch.setattr(ws_client.websockets, "connect", fake_connect, raising=False)

    async def runner():
        async with ws_client.WebSocketClient() as client:
            response = await client.send_command({"cmd": "ping"})
        return response

    response = asyncio.run(runner())

    assert response == {"status": "ok"}
    assert dummy_ws.sent == [json.dumps({"cmd": "ping"})]
    assert dummy_ws.closed is True


def test_parameter_uri_and_manual_start_stop(monkeypatch):
    from Client.network import ws_client

    class DummyWebSocket:
        def __init__(self):
            self.closed = False

        async def send(self, data):
            self.data = data

        async def recv(self):
            return json.dumps({"status": "ok"})

        async def close(self):
            self.closed = True

    dummy_ws = DummyWebSocket()

    async def fake_connect(uri):
        assert uri == "ws://param"
        return dummy_ws

    monkeypatch.setattr(ws_client.websockets, "connect", fake_connect, raising=False)

    async def runner():
        client = ws_client.WebSocketClient("ws://param")
        await client.connect()
        response = await client.send_command({"cmd": "ping"})
        await client.close()
        return response

    response = asyncio.run(runner())

    assert response == {"status": "ok"}
    assert dummy_ws.data == json.dumps({"cmd": "ping"})
    assert dummy_ws.closed is True

