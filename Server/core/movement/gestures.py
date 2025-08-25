"""Gesture interpolation utilities for quadruped controller.

This module defines a :class:`Gestures` helper responsible for handling
scripted gestures that move the robot legs through absolute positions over
time. Gestures are represented as a sequence of keyframes; each keyframe is a
list of absolute leg coordinates ``[[x,y,z], ...]`` for the four legs and a
duration in seconds. ``Gestures`` interpolates linearly between consecutive
keyframes when ``update`` is called.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple


class Gestures:
    """Manager for scripted leg gestures.

    Parameters
    ----------
    controller:
        The movement controller that owns the leg ``point`` positions.  The
        controller is expected to expose ``point`` as a list ``[[x,y,z], ...]``
        which will be modified in-place by :meth:`update`.
    """

    #: Convenience aliases for indexing legs/axes
    FL, RL, RR, FR = 0, 1, 2, 3
    X, Y, Z = 0, 1, 2

    def __init__(self, controller) -> None:
        self.controller = controller
        self._active: bool = False
        self._sequence: List[Tuple[float, List[List[float]]]] = []
        self._index: int = 0
        self._elapsed: float = 0.0
        self._start_pos: List[List[float]] | None = None

        # Library of available gestures.  Each entry is a list of
        # ``(duration, positions)`` pairs where ``positions`` is a
        # ``4 x 3`` matrix of absolute leg coordinates.
        self._library = {
            "greet": [
                # Move to initial greeting pose
                (0.6, [[-20, 120, -40], [50, 105, 0], [50, 105, 0], [0, 120, 0]]),
                # Lift front-right leg forward
                (0.4, [[-20, 120, -40], [50, 105, 0], [50, 105, 0], [80, 23, 0]]),
                # Return front-right leg
                (0.4, [[-20, 120, -40], [50, 105, 0], [50, 105, 0], [0, 120, 0]]),
                # Go back to neutral standing position
                (0.6, [[55, 78, 0], [55, 78, 0], [55, 78, 0], [55, 78, 0]]),
            ]
        }

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def active(self) -> bool:
        """Return ``True`` if a gesture is currently running."""
        return self._active

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self, name: str) -> None:
        """Begin the gesture identified by ``name``.

        Any running gesture is cancelled.  The controller's locomotion is
        disabled while the gesture is active by setting
        ``controller._locomotion_enabled`` to ``False`` and stopping any
        ongoing CPG cycle via ``controller.stop()``.
        """
        seq = self._library.get(name)
        if not seq:
            return

        # Stop any previous gesture and locomotion
        self.cancel()
        # Ensure the robot is stationary before starting the gesture
        if hasattr(self.controller, "stop"):
            self.controller.stop()

        self._sequence = seq
        self._index = 0
        self._elapsed = 0.0
        # Capture starting positions for interpolation
        self._start_pos = [p[:] for p in self.controller.point]
        self._active = True

        # Disable locomotion while the gesture is active
        setattr(self.controller, "_locomotion_enabled", False)

    def cancel(self) -> None:
        """Abort the current gesture, if any, and re-enable locomotion."""
        self._active = False
        self._sequence = []
        self._index = 0
        self._elapsed = 0.0
        self._start_pos = None
        setattr(self.controller, "_locomotion_enabled", True)

    def update(self, dt: float) -> bool:
        """Advance the current gesture.

        Parameters
        ----------
        dt:
            Time in seconds since the previous call.

        Returns
        -------
        bool
            ``True`` when the gesture has finished, otherwise ``False``.
        """
        if not self._active or not self._sequence:
            return False

        duration, target = self._sequence[self._index]
        self._elapsed += dt
        fraction = min(1.0, duration and self._elapsed / duration)

        # Linear interpolation between the starting pose and the target pose
        assert self._start_pos is not None
        for leg in range(4):
            for axis in range(3):
                start_val = self._start_pos[leg][axis]
                end_val = target[leg][axis]
                self.controller.point[leg][axis] = (
                    start_val + (end_val - start_val) * fraction
                )

        if fraction >= 1.0:
            # Move to the next keyframe
            self._start_pos = [p[:] for p in target]
            self._elapsed = 0.0
            self._index += 1
            if self._index >= len(self._sequence):
                # Gesture complete
                self.cancel()
                return True
        return False
