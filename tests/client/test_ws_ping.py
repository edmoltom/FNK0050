import asyncio
import pytest


def test_ws_ping(ws_client, event_loop):
    async def run():
        response = await ws_client.send_command({'cmd': 'ping'})
        assert response['reply'] == 'pong'
    event_loop.run_until_complete(run())
