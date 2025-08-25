"""High level movement controller.

This module provides a thin wrapper around :class:`~Control.Control` that
exposes a compact API for higher level components.  It combines the
capabilities of the base :class:`Control` class (gait generation, servo
communication, etc.) with the :class:`Gestures` engine to allow scripted leg
motions.

The public API is intentionally small:

``greet()``
    Run the built‑in greeting gesture.
``gesture(name)``
    Start any gesture stored in :class:`Gestures` by name.
``update(dt)``
    Advance the controller by ``dt`` seconds, updating gestures or normal
    locomotion and sending servo commands.
``set_servo_angle(channel, angle)``
    Convenience wrapper to set a servo angle without importing the
    :class:`Servo` class elsewhere.

These methods centralise servo interactions and provide guidance for adding
future gestures.
"""

from __future__ import annotations

from Control import Control
from .gestures import Gestures


class Controller(Control):
    """Extension of :class:`Control` that adds gesture management."""

    def __init__(self) -> None:
        super().__init__()
        # ``Gestures`` manipulates ``self.point`` directly and will set
        # ``_locomotion_enabled`` when running a gesture.
        self.gestures = Gestures(self)
        self._locomotion_enabled = True

    # ------------------------------------------------------------------
    # High level public API
    # ------------------------------------------------------------------
    def set_servo_angle(self, channel: int, angle: float) -> None:
        """Set ``channel`` to ``angle`` degrees via the internal servo."""
        self.servo.setServoAngle(channel, angle)

    def greet(self) -> None:
        """Run the built in ``greet`` gesture."""
        self.gesture("greet")

    def gesture(self, name: str) -> None:
        """Start a gesture by ``name`` if present in the library."""
        self.gestures.start(name)

    def update(self, dt: float) -> None:
        """Advance the controller by ``dt`` seconds and send servo commands."""
        self.update_legs_from_cpg(dt)
        self.run()

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    def relax(self, flag: bool = False) -> None:
        """Relax the robot and cancel any active gesture."""
        if self.gestures.active:
            self.gestures.cancel()
        super().relax(flag)

    def update_legs_from_cpg(self, dt: float) -> None:  # type: ignore[override]
        """Update leg positions and handle gestures before CPG updates."""
        if self.gestures.active:
            finished = self.gestures.update(dt)
            if finished:
                self._locomotion_enabled = True
            return

        if not self._locomotion_enabled:
            return

        super().update_legs_from_cpg(dt)

