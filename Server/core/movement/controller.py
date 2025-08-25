"""Movement controller with gesture support.

This module subclasses :class:`Control` to integrate the :class:`Gestures`
helper.  The controller exposes the ``gestures`` attribute for managing
gestures.  During each update cycle ``gestures.update`` is invoked before any
CPG updates, and locomotion is skipped while a gesture is active.
"""

from __future__ import annotations

from Control import Control
from .gestures import Gestures


class Controller(Control):
    """Extension of :class:`Control` that adds gesture management."""

    def __init__(self):
        super().__init__()
        # ``Gestures`` manipulates ``self.point`` directly.
        self.gestures = Gestures(self)
        # Flag used to temporarily disable locomotion when a gesture runs
        self._locomotion_enabled = True

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    def relax(self, flag: bool = False):
        """Relax the robot and cancel any active gesture."""
        if self.gestures.active:
            self.gestures.cancel()
        super().relax(flag)

    def update_legs_from_cpg(self, dt: float):
        """Update leg positions.

        Gestures, if active, are processed before any CPG updates.  When a
        gesture is active, locomotion (CPG updates) is suspended until the
        gesture has finished.
        """
        if self.gestures.active:
            finished = self.gestures.update(dt)
            if finished:
                self._locomotion_enabled = True
            return

        if not self._locomotion_enabled:
            return

        super().update_legs_from_cpg(dt)
