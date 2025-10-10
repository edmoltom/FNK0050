import sys
from pathlib import Path
import time
import pytest

from mind.proprioception.body_model import BodyModel
from mind.proprioception.sensor_bus import SensorBus

def test_sensorbus_odometry_update():
    """Verify that SensorBus updates BodyModel correctly from odometry packets."""
    body = BodyModel()
    bus = SensorBus(body)

    # Initial state
    start_state = body.summary()

    # Simulate a packet from odometry
    packet = {
        "sensor": "odometry",
        "timestamp": time.time(),
        "type": "relative",
        "data": {"dx": 0.10, "dy": 0.05, "dtheta": 0.1},
        "confidence": 0.8,
    }

    bus.receive(packet)

    # After update, the body pose should have changed
    new_state = body.summary()

    # Position changed
    assert new_state["x"] != start_state["x"]
    assert new_state["y"] != start_state["y"]

    # Orientation wrapped correctly (0 ≤ θ < 2π)
    assert 0.0 <= new_state["theta"] < 6.2832

    # Confidence adjusted toward 0.8
    assert 0.7 < body.confidence <= 1.0


def test_sensorbus_environmental_data_does_not_change_pose():
    """Environmental data should not affect the pose directly."""
    body = BodyModel()
    bus = SensorBus(body)

    before = body.summary()

    env_packet = {
        "sensor": "ultrasonic",
        "type": "environmental",
        "data": {"distance": 0.25, "angle": 45},
        "confidence": 0.9,
    }

    bus.receive(env_packet)
    after = body.summary()

    # Pose should remain unchanged
    assert after["x"] == before["x"]
    assert after["y"] == before["y"]
    assert after["theta"] == before["theta"]


def test_sensorbus_handles_invalid_packets_gracefully():
    """SensorBus should not crash when receiving malformed packets."""
    body = BodyModel()
    bus = SensorBus(body)

    try:
        bus.receive("not_a_dict")
        bus.receive({"sensor": "odometry"})  # missing keys
    except Exception as e:
        pytest.fail(f"SensorBus raised an unexpected exception: {e}")
