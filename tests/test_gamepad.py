import pytest

Gamepad = pytest.importorskip("Gamepad")
pytest.importorskip("Server.core.Action")


def test_gamepad_has_xbox360():
    assert hasattr(Gamepad, "Xbox360")
