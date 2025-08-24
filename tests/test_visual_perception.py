import pytest

camera_module = pytest.importorskip("Server.core.Camera")


def test_camera_class_exists():
    assert hasattr(camera_module, "Camera")
