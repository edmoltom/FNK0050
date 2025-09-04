from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import logging

from control.pid import Incremental_PID

from core.MovementControl import MovementControl
from core.VisionManager import VisionManager


def _clamp(val: float, mn: float, mx: float) -> float:
    """Clamp ``val`` between ``mn`` and ``mx``."""
    return max(mn, min(mx, val))


class FaceTracker:
    """Simple face-based head tracking controller."""

    def __init__(self, movement: MovementControl, vision: Optional[VisionManager] = None) -> None:
        self.movement = movement
        self.vision = vision
        self.pid = Incremental_PID(20.0, 0.0, 5.0)
        self.pid.setPoint = 0.0
        self.pid_scale = 0.1
        self.current_head_deg = movement.head_limits[2]
        self._had_face = False
        self._ema_center: Optional[float] = None
        self._face_count = 0
        self._miss_count = 0
        self._locked = False
        self.logger = logging.getLogger("face_tracker")

    def _select_largest_face(self, faces: List[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if not faces:
            return None
        return max(faces, key=lambda f: float(f.get("w", 0.0)) * float(f.get("h", 0.0)))

    def update(self, result: Dict | None, dt: float) -> None:
        """Update head position based on vision ``result`` and timestep ``dt``."""
        min_deg, max_deg, center = self.movement.head_limits
        faces = result.get("faces") if result else None
        if not faces:
            if self._had_face:
                self.logger.info("Lost face detection")
                self._had_face = False
            self._ema_center = None
            self._face_count = 0
            self._miss_count += 1
            if self._locked and self._miss_count >= 5:
                self._locked = False
                if self.vision:
                    self.vision.set_roi(None)
                self.logger.info("Face lock released")
            diff = center - self.current_head_deg
            if abs(diff) < 0.1:
                return
            max_step = 30.0 * dt
            step = _clamp(diff, -max_step, max_step)
            self.current_head_deg += step
            self.current_head_deg = _clamp(self.current_head_deg, min_deg, max_deg)
            self.movement.head_deg(self.current_head_deg, duration_ms=100)
            return

        face = self._select_largest_face(faces)
        if not face:
            return

        self._miss_count = 0
        self._face_count += 1
        if not self._locked and self._face_count >= 3:
            self._locked = True
            self.logger.info("Face lock acquired")

        if not self._had_face:
            self.logger.info("Face detected")
            self._had_face = True

        space = result.get("space", (0, 0))
        space_w = float(space[0]) if len(space) > 0 else 0.0
        space_h = float(space[1]) if len(space) > 1 else 0.0
        if space_h <= 0:
            return

        x = float(face.get("x", 0.0))
        y = float(face.get("y", 0.0))
        w = float(face.get("w", 0.0))
        h = float(face.get("h", 0.0))
        face_center_y = y + h / 2.0
        if self._ema_center is None:
            self._ema_center = face_center_y
        else:
            self._ema_center = 0.2 * face_center_y + 0.8 * self._ema_center
        error = (self._ema_center - space_h / 2.0) / (space_h / 2.0)
        if abs(error) >= 0.05:
            delta = self.pid.PID_compute(error) * self.pid_scale
            delta = _clamp(delta, -3.0, 3.0)
            target = _clamp(self.current_head_deg + delta, min_deg, max_deg)
            self.current_head_deg = target
            self.movement.head_deg(self.current_head_deg, duration_ms=100)
            self.logger.debug("error=%.3f, delta=%.2f, target=%.1f", error, delta, target)

        margin_x = w * 0.2
        margin_y = h * 0.2
        roi_x = max(0, int(x - margin_x))
        roi_y = max(0, int(y - margin_y))
        roi_w = int(min(space_w - roi_x, w + 2 * margin_x))
        roi_h = int(min(space_h - roi_y, h + 2 * margin_y))
        if self.vision:
            if self._locked:
                self.vision.set_roi((roi_x, roi_y, roi_w, roi_h))
            else:
                self.vision.set_roi(None)
