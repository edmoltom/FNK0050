from __future__ import annotations

from typing import Dict, List, Optional
import logging

from control.pid import Incremental_PID

from core.MovementControl import MovementControl


def _clamp(val: float, mn: float, mx: float) -> float:
    """Clamp ``val`` between ``mn`` and ``mx``."""
    return max(mn, min(mx, val))


class FaceTracker:
    """Simple face-based head tracking controller."""

    def __init__(self, movement: MovementControl) -> None:
        self.movement = movement
        self.pid = Incremental_PID(20.0, 0.0, 5.0)
        self.pid.setPoint = 0.0
        self.pid_scale = 0.1
        self.current_head_deg = movement.head_limits[2]
        self._had_face = False
        self.logger = logging.getLogger("face_tracker")

    def _select_largest_face(self, faces: List[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if not faces:
            return None
        return max(faces, key=lambda f: float(f.get("w", 0.0)) * float(f.get("h", 0.0)))

    def update(self, result: Dict | None, dt: float) -> None:
        """Update head position based on vision ``result`` and timestep ``dt``."""
        min_deg, max_deg, center = self.movement.head_limits
        if not result or not result.get("faces"):
            if self._had_face:
                self.logger.info("Lost face detection")
                self._had_face = False
            diff = center - self.current_head_deg
            if abs(diff) < 0.1:
                return
            max_step = 30.0 * dt
            step = _clamp(diff, -max_step, max_step)
            self.current_head_deg += step
            self.current_head_deg = _clamp(self.current_head_deg, min_deg, max_deg)
            self.movement.head_deg(self.current_head_deg, duration_ms=100)
            return

        face = self._select_largest_face(result.get("faces", []))
        if not face:
            if self._had_face:
                self.logger.info("Lost face detection")
                self._had_face = False
            return

        if not self._had_face:
            self.logger.info("Face detected")
            self._had_face = True

        space = result.get("space", (0, 0))
        space_h = float(space[1]) if len(space) > 1 else 0.0
        if space_h <= 0:
            return
        face_center_y = float(face.get("y", 0.0)) + float(face.get("h", 0.0)) / 2.0
        error = (face_center_y - space_h / 2.0) / (space_h / 2.0)
        if abs(error) < 0.05:
            return
        delta = self.pid.PID_compute(error) * self.pid_scale
        target = _clamp(self.current_head_deg + delta, min_deg, max_deg)
        self.current_head_deg = target
        self.movement.head_deg(self.current_head_deg, duration_ms=100)
        self.logger.debug("error=%.3f, delta=%.2f, target=%.1f", error, delta, target)
