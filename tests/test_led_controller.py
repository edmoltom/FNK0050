import pytest

led_controller_module = pytest.importorskip("Server.core.LedController")


def test_led_controller_class_exists():
    assert hasattr(led_controller_module, "LedController")
