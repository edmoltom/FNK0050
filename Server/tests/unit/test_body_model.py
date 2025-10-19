import math
import sys
import math

import pytest

from Server.mind.proprioception.body_model import BodyModel


def test_body_model_relative_odometry_update():
    body = BodyModel()
    start_state = body.summary()

    body.correct_with_sensor(
        "odometry",
        {"dx": 0.1, "dy": 0.05, "dtheta": 0.2},
        kind="relative",
        confidence=0.8,
    )

    new_state = body.summary()
    assert new_state["x"] != start_state["x"]
    assert new_state["y"] != start_state["y"]
    assert 0.0 <= new_state["theta"] < 2 * math.pi
    assert 0.7 < body.confidence <= 1.0


def test_body_model_imu_updates_orientation():
    body = BodyModel()
    body.correct_with_sensor(
        "imu",
        {"yaw": 90.0, "pitch": 1.5, "roll": -2.0},
        kind="absolute",
        confidence=0.6,
    )

    assert math.isclose(body.theta, math.radians(90.0), rel_tol=1e-3)
    assert body.v == pytest.approx(1.5)
    assert body.w == pytest.approx(-2.0)
    assert 0.5 < body.confidence <= 1.0


def test_body_model_handles_invalid_packets_gracefully():
    body = BodyModel()

    body.correct_with_sensor("odometry", None)
    body.correct_with_sensor("odometry", {"dx": 0.1})
    body.correct_with_sensor("unknown", {"foo": "bar"})

    assert body.summary()["x"] == 0.0
    assert body.summary()["y"] == 0.0
    assert body.summary()["theta"] == 0.0
