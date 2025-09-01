import sys
import types
import asyncio
import json
import threading
import time
from pathlib import Path

import pytest

# Stub websockets module
class FakeWebSocket:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.sent = []

    async def send(self, message):
        data = json.loads(message)
        self.sent.append(data)
        if data.get("cmd") == "stream_start":
            await self.queue.put(json.dumps({"type": "image", "frame": "frame"}))

    async def recv(self):
        return await self.queue.get()

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.queue.get()

    async def close(self):
        pass

fake_ws_holder = {}

async def fake_connect(uri):
    ws = FakeWebSocket()
    fake_ws_holder["ws"] = ws
    return ws

sys.modules['websockets'] = types.SimpleNamespace(connect=fake_connect)

ROOT = Path(__file__).resolve().parents[3] / "Client"
sys.path.insert(0, str(ROOT))
from network.ws_client import WebSocketClient


def test_start_and_stop_stream():
    client = WebSocketClient()
    client.uri = "ws://test"
    frames = []
    evt = threading.Event()

    def callback(frame):
        frames.append(frame)
        evt.set()

    client.start_stream(callback)
    assert evt.wait(1)
    assert frames == ["frame"]
    evt.clear()

    client.stop_stream()

    ws = fake_ws_holder["ws"]
    asyncio.run_coroutine_threadsafe(ws.queue.put(json.dumps({"type": "image", "frame": "after"})), client.loop)
    time.sleep(0.1)
    assert not evt.is_set()
    assert client.receive_task is None
    assert any(cmd.get("cmd") == "stream_start" for cmd in ws.sent)
    assert any(cmd.get("cmd") == "stream_stop" for cmd in ws.sent)
    client.close()
