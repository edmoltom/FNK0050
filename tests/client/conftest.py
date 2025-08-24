import asyncio
import json
import pytest
import socket

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def unused_tcp_port():
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest.fixture
def ws_server(event_loop, unused_tcp_port):
    websockets = pytest.importorskip('websockets')

    async def handler(websocket):
        async for message in websocket:
            data = json.loads(message)
            if data.get('cmd') == 'ping':
                await websocket.send(json.dumps({'status': 'ok', 'reply': 'pong'}))
            else:
                await websocket.send(json.dumps({'status': 'ok', 'received': data}))

    server = event_loop.run_until_complete(
        websockets.serve(handler, 'localhost', unused_tcp_port)
    )
    uri = f'ws://localhost:{unused_tcp_port}'
    yield uri
    server.close()
    event_loop.run_until_complete(server.wait_closed())

@pytest.fixture
def ws_client(event_loop, ws_server):
    pytest.importorskip('websockets')
    from network.ws_client import WebSocketClient

    client = WebSocketClient(uri=ws_server)
    event_loop.run_until_complete(client.connect())
    yield client
    event_loop.run_until_complete(client.close())
