import asyncio
import pytest


def test_ws_command(ws_client, event_loop):
    async def run():
        response = await ws_client.send_command({'cmd': 'process', 'blur': 'true'})
        assert response['received'] == {'cmd': 'process', 'blur': 'true'}
    event_loop.run_until_complete(run())
