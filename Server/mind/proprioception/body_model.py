"""Core classes for Lumo's proprioception subsystem."""

from __future__ import annotations

import math
import time
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BodyModel:
    """Represents Lumo's internal sense of its own position and motion."""

    def __init__(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.v = 0.0
        self.w = 0.0
        self.confidence = 1.0
        self.timestamp = time.time()

    # ---------------------------------------------------------------------
    # Update helpers
    # ---------------------------------------------------------------------
    def update_odometry(self, dx: float, dy: float, dtheta: float) -> None:
        """Predictive update from relative movement data."""

        self.x += dx
        self.y += dy
        self.theta = (self.theta + dtheta) % (2 * math.pi)
        self.timestamp = time.time()
        logger.debug(
            "[BODY] Δx=%.2f Δy=%.2f Δθ=%.2f -> pose=(%.2f, %.2f, %.2f)",
            dx,
            dy,
            dtheta,
            self.x,
            self.y,
            self.theta,
        )

    def correct_with_sensor(
        self,
        sensor: str,
        data: Dict[str, Any] | None,
        *,
        kind: str = "relative",
        confidence: float = 1.0,
    ) -> None:
        """Fuse a sensor reading directly into the body model."""

        if not isinstance(data, dict):
            logger.debug("[BODY] Ignoring %s sensor update without data", sensor)
            return

        handler = {
            "odometry": self._handle_odometry,
            "imu": self._handle_imu,
        }.get(sensor, self._handle_generic)

        handled = handler(data, kind)
        if handled:
            self._adjust_confidence(confidence)
            self.timestamp = time.time()

    # ------------------------------------------------------------------
    # Individual sensor handlers
    # ------------------------------------------------------------------
    def _handle_odometry(self, data: Dict[str, Any], kind: str) -> bool:
        if {"dx", "dy", "dtheta"} <= data.keys():
            self.update_odometry(
                float(data["dx"]),
                float(data["dy"]),
                float(data["dtheta"]),
            )
            return True

        if {"x", "y", "theta"} <= data.keys():
            self.x = float(data["x"])
            self.y = float(data["y"])
            self.theta = float(data["theta"]) % (2 * math.pi)
            logger.debug(
                "[BODY] Absolute pose update -> pose=(%.2f, %.2f, %.2f)",
                self.x,
                self.y,
                self.theta,
            )
            return True

        logger.debug("[BODY] Unsupported odometry payload for kind '%s': %s", kind, data)
        return False

    def _handle_imu(self, data: Dict[str, Any], kind: str) -> bool:  # noqa: ARG002
        yaw = data.get("yaw")
        pitch = data.get("pitch")
        roll = data.get("roll")
        if yaw is None and pitch is None and roll is None:
            logger.debug("[BODY] IMU packet missing orientation data: %s", data)
            return False

        if yaw is not None:
            self.theta = math.radians(float(yaw)) % (2 * math.pi)
        if pitch is not None:
            self.v = float(pitch)
        if roll is not None:
            self.w = float(roll)
        logger.debug(
            "[BODY] IMU update -> yaw=%.2f pitch=%.2f roll=%.2f",
            float(yaw) if yaw is not None else float("nan"),
            float(pitch) if pitch is not None else float("nan"),
            float(roll) if roll is not None else float("nan"),
        )
        return True

    def _handle_generic(self, data: Dict[str, Any], kind: str) -> bool:  # noqa: ARG002
        logger.debug("[BODY] Received data from unsupported sensor: %s", data)
        return False

    def _adjust_confidence(self, conf: float) -> None:
        alpha = 0.2
        self.confidence = (1 - alpha) * self.confidence + alpha * float(conf)

    # ------------------------------------------------------------------
    # Presentation helpers
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, float]:
        return {
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "theta": round(self.theta, 3),
            "confidence": round(self.confidence, 2),
        }
