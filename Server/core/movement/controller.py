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
``cancel()``
    Abort any running gesture and return the robot to a safe stance.
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
        self._gait_enabled = True

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

    def cancel(self) -> None:
        """Cancel any active gesture and return to a safe stance.

        This delegates to :meth:`gestures.cancel` to clear any gesture state,
        re-enables normal gait and invokes the base controller's ``stop``
        implementation to place the robot back into its neutral stance.
        """
        self.gestures.cancel()
        # ``Gestures.cancel`` already restores locomotion and gait, but we
        # make the locomotion flag explicit here for clarity.
        self._locomotion_enabled = True
        Control.stop(self)

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    def relax(self, flag: bool = False) -> None:  # type: ignore[override]
        """Relax the robot, cancelling any active gesture first."""
        if hasattr(self, "gestures"):
            self.cancel()
        if flag:
            # ``Control.relax(True)`` moves the robot to its neutral standing
            # pose without calling ``stop`` again.
            Control.relax(self, True)

    def update_legs_from_cpg(self, dt: float) -> None:  # type: ignore[override]
        """Update leg positions and handle gestures before CPG updates."""
        if self.gestures.active:
            finished = self.gestures.update(dt)
            if finished:
                self._locomotion_enabled = True
            return

        if not self._locomotion_enabled or not self._gait_enabled:
            return

        super().update_legs_from_cpg(dt)

    def stop(self) -> None:  # type: ignore[override]
        """Stop locomotion and cancel any active gesture."""
        self.cancel()

