"""Generic object tracking helpers used by high level controllers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Sequence, Tuple
import logging

from control.pid import Incremental_PID

from core.MovementControl import MovementControl
from core.VisionManager import VisionManager


def _clamp(value: float, mn: float, mx: float) -> float:
    """Clamp ``value`` between ``mn`` and ``mx``."""

    return max(mn, min(mx, value))


def _select_largest_box(
    targets: Sequence[Dict[str, float]]
) -> Optional[Dict[str, float]]:
    """Return the target with the largest area."""

    if not targets:
        return None
    return max(
        targets,
        key=lambda box: float(box.get("w", 0.0)) * float(box.get("h", 0.0)),
    )


def _extract_targets(result: Optional[Dict[str, object]]) -> list[Dict[str, float]]:
    """Extract a list of bounding boxes from ``result``."""

    if not result:
        return []
    for key in ("targets", "faces"):
        raw = result.get(key)
        if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes)):
            return [box for box in raw if isinstance(box, dict)]
    return []


def _extract_space(result: Optional[Dict[str, object]]) -> Optional[Tuple[float, float]]:
    """Return ``(width, height)`` from ``result`` when available."""

    if not result:
        return None
    space = result.get("space")
    if not isinstance(space, Sequence) or isinstance(space, (str, bytes)):
        return None
    if len(space) < 2:
        return None
    try:
        return float(space[0]), float(space[1])
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None


@dataclass
class AxisXTurnController:
    """Controller orchestrating horizontal turns when the target drifts."""

    movement: MovementControl
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("object_tracker.turn")
    )
    deadband_x: float = 0.12
    k_turn: float = 0.8
    base_pulse_ms: int = 120
    min_pulse_ms: int = 60
    max_pulse_ms: int = 180
    turn_speed: float = 0.3
    enabled: bool = True
    _turn_cooldown: float = field(default=0.0, init=False)

    def tick(self, dt: float) -> None:
        """Progress the internal cooldown timer."""

        if self._turn_cooldown > 0.0:
            self._turn_cooldown = max(0.0, self._turn_cooldown - max(0.0, dt))

    def reset(self) -> None:
        """Reset cooldown state."""

        self._turn_cooldown = 0.0

    def update(self, ex: float, dt: float) -> None:
        """Turn the robot left/right based on horizontal error ``ex``."""

        self.tick(dt)
        if not self.enabled or self._turn_cooldown > 0.0:
            return
        if abs(ex) <= self.deadband_x:
            return

        scale = min(1.0, abs(ex) * self.k_turn)
        pulse = int(_clamp(self.base_pulse_ms * scale, self.min_pulse_ms, self.max_pulse_ms))
        if pulse <= 0:
            return

        if ex > 0:
            self.movement.turn_right(duration_ms=pulse, speed=self.turn_speed)
        else:
            self.movement.turn_left(duration_ms=pulse, speed=self.turn_speed)
        self._turn_cooldown = pulse / 1000.0

    # ----- Compatibility helpers -------------------------------------------------
    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def set_deadband(self, deadband: float) -> None:
        self.deadband_x = float(deadband)

    def set_pulses(self, *, base: int, minimum: int, maximum: int) -> None:
        self.base_pulse_ms = int(base)
        self.min_pulse_ms = int(minimum)
        self.max_pulse_ms = int(maximum)

    def set_turn_gain(self, gain: float) -> None:
        self.k_turn = float(gain)

    def set_turn_speed(self, speed: float) -> None:
        self.turn_speed = float(speed)


@dataclass
class AxisYHeadController:
    """Vertical head controller using EMA and PID smoothing."""

    movement: MovementControl
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("object_tracker.head")
    )
    pid: Incremental_PID = field(default_factory=lambda: Incremental_PID(20.0, 0.0, 5.0))
    pid_scale: float = 0.1
    ema_alpha: float = 0.2
    error_threshold: float = 0.05
    delta_limit_deg: float = 3.0
    head_duration_ms: int = 100
    recenter_speed_deg: float = 5.0
    recenter_duration_ms: int = 150
    enabled: bool = True
    _ema_center: Optional[float] = field(default=None, init=False)
    current_head_deg: float = field(init=False)

    def __post_init__(self) -> None:
        self.pid.setPoint = 0.0
        self.current_head_deg = self.movement.head_limits[2]

    def reset(self) -> None:
        """Clear EMA state after losing the target."""

        self._ema_center = None

    def _apply_head_delta(self, delta: float) -> None:
        min_deg, max_deg, _ = self.movement.head_limits
        target = _clamp(self.current_head_deg + delta, min_deg, max_deg)
        if target == self.current_head_deg:
            return
        self.current_head_deg = target
        self.movement.head_deg(self.current_head_deg, duration_ms=self.head_duration_ms)

    def update(
        self,
        target: Dict[str, float],
        space: Tuple[float, float],
        dt: float,
    ) -> Optional[float]:
        """Update PID control using ``target`` and ``space`` information."""

        del dt  # Unused but kept for API symmetry with :class:`AxisXTurnController`.

        space_h = float(space[1])
        if space_h <= 0.0:
            return None

        y = float(target.get("y", 0.0))
        h = float(target.get("h", 0.0))
        face_center_y = y + h / 2.0

        if self._ema_center is None:
            self._ema_center = face_center_y
        else:
            alpha = self.ema_alpha
            self._ema_center = alpha * face_center_y + (1.0 - alpha) * self._ema_center

        mid = space_h / 2.0
        if mid <= 0.0:
            return None

        error = (self._ema_center - mid) / mid
        if abs(error) < self.error_threshold:
            return error

        delta = self.pid.PID_compute(error) * self.pid_scale
        delta = _clamp(delta, -self.delta_limit_deg, self.delta_limit_deg)
        if not self.enabled:
            return error
        self._apply_head_delta(delta)
        self.logger.debug("error=%.3f, delta=%.2f, target=%.1f", error, delta, self.current_head_deg)
        return error

    def recenter(self, dt: float) -> None:
        """Slowly recenter the head after prolonged target loss."""

        if not self.enabled:
            return

        min_deg, max_deg, center = self.movement.head_limits
        diff = center - self.current_head_deg
        if diff == 0.0:
            return
        max_step = max(0.0, self.recenter_speed_deg * dt)
        if max_step <= 0.0:
            return
        step = _clamp(diff, -max_step, max_step)
        new_deg = _clamp(self.current_head_deg + step, min_deg, max_deg)
        if new_deg == self.current_head_deg:
            return
        self.current_head_deg = new_deg
        self.movement.head_deg(self.current_head_deg, duration_ms=self.recenter_duration_ms)


@dataclass
class ObjectTracker:
    """High-level helper coordinating per-axis controllers."""

    movement: MovementControl
    vision: VisionManager | None = None
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("object_tracker")
    )
    x: AxisXTurnController = field(init=False)
    y: AxisYHeadController = field(init=False)
    _had_target: bool = field(default=False, init=False)
    _locked: bool = field(default=False, init=False)
    _face_count: int = field(default=0, init=False)
    _miss_count: int = field(default=0, init=False)
    _lock_frames_needed: int = field(default=3, init=False, repr=False)
    _miss_release: int = field(default=5, init=False, repr=False)
    _recenter_after: int = field(default=40, init=False, repr=False)

    def __post_init__(self) -> None:
        self.x = AxisXTurnController(self.movement, self.logger)
        self.y = AxisYHeadController(self.movement, self.logger)
        # Ensure compatibility defaults mirror the legacy constructor values.
        self.lock_frames_needed = 3
        self.miss_release = 5
        self.recenter_after = 40

    # ----- Compatibility helpers -------------------------------------------------
    @property
    def deadband_x(self) -> float:
        return self.x.deadband_x

    @deadband_x.setter
    def deadband_x(self, value: float) -> None:
        self.x.set_deadband(value)

    def set_turn_enabled(self, enabled: bool) -> None:
        self.x.set_enabled(enabled)

    def set_turn_gain(self, gain: float) -> None:
        self.x.set_turn_gain(gain)

    def set_turn_speed(self, speed: float) -> None:
        self.x.set_turn_speed(speed)

    def set_turn_pulses(self, *, base: int, minimum: int, maximum: int) -> None:
        self.x.set_pulses(base=base, minimum=minimum, maximum=maximum)

    def set_enabled(
        self,
        *,
        enable_x: bool | None = None,
        enable_y: bool | None = None,
    ) -> None:
        if enable_x is not None:
            self.x.set_enabled(enable_x)
        if enable_y is not None:
            self.y.enabled = bool(enable_y)

    @property
    def lock_frames_needed(self) -> int:
        return self._lock_frames_needed

    @lock_frames_needed.setter
    def lock_frames_needed(self, value: int) -> None:
        self._lock_frames_needed = max(0, int(value))

    @property
    def miss_release(self) -> int:
        return self._miss_release

    @miss_release.setter
    def miss_release(self, value: int) -> None:
        self._miss_release = max(0, int(value))

    @property
    def recenter_after(self) -> int:
        return self._recenter_after

    @recenter_after.setter
    def recenter_after(self, value: int) -> None:
        self._recenter_after = max(0, int(value))

    # ----- Core behaviour --------------------------------------------------------
    def update(self, result: Optional[Dict[str, object]], dt: float) -> None:
        """Update internal state based on detection ``result``."""

        targets = _extract_targets(result)

        if not targets:
            if self._had_target:
                self.logger.info("Target lost")
                self._had_target = False
            self._face_count = 0
            self._miss_count += 1
            self.y.reset()
            if self._locked and self._miss_count >= self.miss_release:
                self._locked = False
                if self.vision:
                    self.vision.set_roi(None)
                self.logger.info("Target lock released")
            self.movement.stop()
            self.x.tick(dt)
            if self._miss_count >= self.recenter_after:
                self.y.recenter(dt)
            return

        target = _select_largest_box(targets)
        if target is None:
            self.x.tick(dt)
            return

        space = _extract_space(result)
        if not space:
            self.x.tick(dt)
            return

        self._miss_count = 0
        self._face_count += 1
        if not self._locked and self._face_count >= self.lock_frames_needed:
            self._locked = True
            self.logger.info("Target lock acquired")

        if not self._had_target:
            self.logger.info("Target detected")
            self._had_target = True

        space_w, space_h = space
        x = float(target.get("x", 0.0))
        y = float(target.get("y", 0.0))
        w = float(target.get("w", 0.0))
        h = float(target.get("h", 0.0))

        face_center_x = x + w / 2.0
        ex = (face_center_x - space_w / 2.0) / (space_w / 2.0) if space_w > 0 else 0.0
        self.x.update(ex, dt)

        self.y.update(target, (space_w, space_h), dt)

        if self.vision:
            if self._locked:
                margin_x = w * 0.2
                margin_y = h * 0.2
                roi_x = max(0, int(x - margin_x))
                roi_y = max(0, int(y - margin_y))
                roi_w = int(min(space_w - roi_x, w + 2 * margin_x))
                roi_h = int(min(space_h - roi_y, h + 2 * margin_y))
                self.vision.set_roi((roi_x, roi_y, roi_w, roi_h))
            else:
                self.vision.set_roi(None)

