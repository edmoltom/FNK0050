import pytest

led_module = pytest.importorskip("Server.core.led.led")


def test_led_class_exists():
    assert hasattr(led_module, "Led")
