from __future__ import annotations
from typing import Dict, List, Optional
import logging

from core.MovementControl import MovementControl
from core.VisionManager import VisionManager

from .tracker import ObjectTracker


class FaceTracker:
    """Simple face-based head tracking controller."""

    def __init__(self, movement: MovementControl, vision: Optional[VisionManager] = None) -> None:
        self.movement = movement
        self.vision = vision
        self.logger = logging.getLogger("face_tracker")
        self.tracker = ObjectTracker(movement, vision, logger=self.logger)

    # ----- Compatibility helpers -------------------------------------------------
    @property
    def deadband_x(self) -> float:
        return self.tracker.deadband_x

    @deadband_x.setter
    def deadband_x(self, value: float) -> None:
        self.tracker.deadband_x = value

    @property
    def turn_enabled(self) -> bool:
        return self.tracker.x.enabled

    @turn_enabled.setter
    def turn_enabled(self, enabled: bool) -> None:
        self.tracker.set_turn_enabled(enabled)

    @property
    def enable_x(self) -> bool:
        return self.tracker.x.enabled

    @enable_x.setter
    def enable_x(self, enabled: bool) -> None:
        self.tracker.set_enabled(enable_x=bool(enabled))

    @property
    def enable_y(self) -> bool:
        return self.tracker.y.enabled

    @enable_y.setter
    def enable_y(self, enabled: bool) -> None:
        self.tracker.set_enabled(enable_y=bool(enabled))

    @property
    def min_pulse_ms(self) -> int:
        return self.tracker.x.min_pulse_ms

    @min_pulse_ms.setter
    def min_pulse_ms(self, value: int) -> None:
        self.tracker.set_turn_pulses(
            base=self.tracker.x.base_pulse_ms,
            minimum=int(value),
            maximum=self.tracker.x.max_pulse_ms,
        )

    @property
    def max_pulse_ms(self) -> int:
        return self.tracker.x.max_pulse_ms

    @max_pulse_ms.setter
    def max_pulse_ms(self, value: int) -> None:
        self.tracker.set_turn_pulses(
            base=self.tracker.x.base_pulse_ms,
            minimum=self.tracker.x.min_pulse_ms,
            maximum=int(value),
        )

    @property
    def base_pulse_ms(self) -> int:
        return self.tracker.x.base_pulse_ms

    @base_pulse_ms.setter
    def base_pulse_ms(self, value: int) -> None:
        self.tracker.set_turn_pulses(
            base=int(value),
            minimum=self.tracker.x.min_pulse_ms,
            maximum=self.tracker.x.max_pulse_ms,
        )

    @property
    def k_turn(self) -> float:
        return self.tracker.x.k_turn

    @k_turn.setter
    def k_turn(self, value: float) -> None:
        self.tracker.set_turn_gain(value)

    @property
    def current_head_deg(self) -> float:
        return self.tracker.y.current_head_deg

    @current_head_deg.setter
    def current_head_deg(self, value: float) -> None:
        self.tracker.y.current_head_deg = float(value)

    def set_enabled(
        self,
        enabled: bool | None = None,
        *,
        enable_x: bool | None = None,
        enable_y: bool | None = None,
    ) -> None:
        """Toggle axis controllers while supporting the legacy interface."""

        if enabled is not None:
            if enable_x is None:
                enable_x = enabled
            if enable_y is None:
                enable_y = enabled
        self.tracker.set_enabled(enable_x=enable_x, enable_y=enable_y)

    def _select_largest_face(self, faces: List[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if not faces:
            return None
        return max(faces, key=lambda f: float(f.get("w", 0.0)) * float(f.get("h", 0.0)))

    def update(self, result: Dict | None, dt: float) -> None:
        """Update head position based on vision ``result`` and timestep ``dt``."""

        self.tracker.update(result, dt)
