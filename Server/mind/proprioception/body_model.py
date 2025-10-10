"""Core classes for Lumo's proprioception subsystem."""

import time
import math
import logging

logger = logging.getLogger(__name__)


class BodyModel:
    """
    Represents Lumo's internal sense of its own position and motion.
    Combines odometry predictions with sensor corrections to maintain
    a coherent body pose in the environment.
    """

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.v = 0.0
        self.w = 0.0
        self.confidence = 1.0
        self.timestamp = time.time()

    def update_odometry(self, dx, dy, dtheta):
        """Predictive update from movement data."""
        self.x += dx
        self.y += dy
        self.theta = (self.theta + dtheta) % (2 * math.pi)
        self.timestamp = time.time()
        logger.debug("[BODY] Δx=%.2f Δy=%.2f Δθ=%.2f -> pose=(%.2f, %.2f, %.2f)",
                     dx, dy, dtheta, self.x, self.y, self.theta)

    def correct_with_sensor(self, correction):
        """Apply sensor-based correction (e.g., distance or orientation)."""
        pass

    def summary(self):
        return {
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "theta": round(self.theta, 3),
            "confidence": round(self.confidence, 2)
        }
