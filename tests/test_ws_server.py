import pytest

ws_module = pytest.importorskip("Server.network.ws_server")


def test_ws_server_start_exists():
    assert hasattr(ws_module, "start_ws_server")
