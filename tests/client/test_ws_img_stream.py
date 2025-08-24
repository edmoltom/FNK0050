import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / 'Client'))
from gui.services.stream_service import StreamService


class DummyClient:
    def __init__(self, response):
        self.response = response

    def send_command(self, command):
        return self.response


class AsyncDummyClient:
    def __init__(self, response):
        self.response = response

    async def send_command(self, command):
        return self.response


@pytest.fixture
def image_response():
    return {'status': 'ok', 'data': 'base64data'}


def test_stream_service_sync(image_response):
    service = StreamService(DummyClient(image_response))
    assert service.fetch_image() == 'base64data'


def test_stream_service_async(image_response):
    service = StreamService(AsyncDummyClient(image_response))
    assert service.fetch_image() == 'base64data'
