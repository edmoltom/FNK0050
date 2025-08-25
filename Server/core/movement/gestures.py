"""Gesture interpolation utilities for the quadruped movement controller.

The module exposes :class:`Gestures`, a helper that plays scripted motion
sequences without blocking the rest of the control loop.  A gesture is
described by keyframes containing **absolute** foot coordinates
``[[x, y, z], ...]`` for the four legs and a matching list of phase
durations.  Calling :meth:`Gestures.update` steps the interpolation toward
the current keyframe's absolute target and returns immediately.

Expected controller interface
-----------------------------
``Gestures`` operates on a movement controller instance and expects the
controller to provide:

* ``point`` – a ``4 x 3`` list of leg coordinates that will be modified
  in place.
* ``_locomotion_enabled`` – a flag toggled while gestures are active.
* ``stop()`` – optional method called before a gesture begins to halt any
  existing motion.

Example
-------
Registering a new gesture with absolute keyframes and running it:

>>> g = Gestures(controller)
>>> g.add_gesture(
...     "bow",
...     [
...         [[55, 78, 0], [55, 78, 0], [55, 78, 0], [55, 78, 0]],
...         [[30, 60, -20], [55, 78, 0], [55, 78, 0], [30, 60, -20]],
...     ],
...     [0.5, 0.5],
... )
>>> g.start("bow")
>>> while g.active:
...     g.update(dt)  # non-blocking

The default timings for built in gestures are::

    DEFAULT_DURATIONS = {
        "greet": [0.6, 0.4, 0.4, 0.6],
    }

Tuning can be achieved by modifying :data:`DEFAULT_DURATIONS`, passing a
``speed`` scalar to :meth:`Gestures.start` or providing an explicit list of
durations via the ``durations`` argument.
"""

from __future__ import annotations

from typing import List, Sequence
import logging


# Default phase durations for built-in gestures.
DEFAULT_DURATIONS = {
    "greet": [0.6, 0.4, 0.4, 0.6],
}


class Gestures:
    """Manager for scripted leg gestures.

    Gestures operate on **absolute** leg coordinates and are advanced in a
    non-blocking manner by calling :meth:`update` with the elapsed time.

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
        # ``_sequence`` holds keyframe positions for the active gesture while
        # ``_durations`` stores the associated phase lengths in seconds.
        self._sequence: List[List[List[float]]] = []
        self._durations: List[float] = []
        self._index: int = 0
        self._elapsed: float = 0.0
        # ``_entry`` stores the stance when the gesture begins so that it is
        # only captured once.  ``_phase_start`` tracks the leg positions at the
        # start of the current keyframe for interpolation toward the absolute
        # target of that keyframe.
        self._entry: List[List[float]] | None = None
        self._phase_start: List[List[float]] | None = None

        # Track controller gait state so it can be restored after a gesture
        self._prev_gait_enabled: bool = True

        # Library of available gestures keyed by name.  Durations for each
        # phase are stored separately in ``_duration_cfg`` to allow external
        # tuning without altering the keyframe coordinates.
        self._library: dict[str, List[List[List[float]]]] = {}
        self._duration_cfg: dict[str, List[float]] = {}

        # Register the built-in greeting gesture.
        self.add_gesture(
            "greet",
            [
                # Move to initial greeting pose
                [[-20, 120, -40], [50, 105, 0], [50, 105, 0], [0, 120, 0]],
                # Lift front-right leg forward
                [[-20, 120, -40], [50, 105, 0], [50, 105, 0], [80, 23, 0]],
                # Return front-right leg
                [[-20, 120, -40], [50, 105, 0], [50, 105, 0], [0, 120, 0]],
                # Go back to neutral standing position
                [[55, 78, 0], [55, 78, 0], [55, 78, 0], [55, 78, 0]],
            ],
            DEFAULT_DURATIONS["greet"],
        )

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
    def supported(self) -> List[str]:
        """Return a list of names for the gestures available."""
        return list(self._library.keys())

    def add_gesture(
        self,
        name: str,
        positions: Sequence[List[List[float]]],
        durations: Sequence[float],
    ) -> None:
        """Register a new gesture under ``name``.

        Parameters
        ----------
        positions:
            Sequence of ``4 x 3`` matrices describing absolute leg coordinates
            for each keyframe.
        durations:
            Duration in seconds for each phase.  Must be the same length as
            ``positions``.
        """
        if len(positions) != len(durations):
            raise ValueError("positions and durations must be the same length")

        self._library[name] = [[p[:] for p in frame] for frame in positions]
        self._duration_cfg[name] = list(durations)

    def start(
        self,
        name: str,
        speed: float = 1.0,
        durations: Sequence[float] | None = None,
    ) -> None:
        """Begin the gesture identified by ``name``.

        Any running gesture is cancelled.  The controller's locomotion is
        disabled while the gesture is active by setting
        ``controller._locomotion_enabled`` to ``False`` and stopping any
        ongoing CPG cycle via ``controller.stop()``.

        Parameters
        ----------
        name:
            Name of the gesture to start.
        speed:
            Scalar applied to default phase durations.  ``2.0`` runs twice as
            fast, ``0.5`` twice as slow.  Ignored if ``durations`` is provided.
        durations:
            Optional list of phase durations overriding the defaults.
        """
        if name not in self._library:
            logging.getLogger(__name__).warning(
                "Unrecognized gesture '%s'", name
            )
            # Cancel any running gesture but do not alter leg positions
            self.cancel()
            return

        # Stop any previous gesture and locomotion
        self.cancel()
        # Ensure the robot is stationary before starting the gesture
        if hasattr(self.controller, "stop"):
            self.controller.stop()

        self._sequence = self._library[name]
        base_durations = self._duration_cfg.get(name, [])
        if durations is not None:
            self._durations = list(durations)
        else:
            self._durations = [d / speed for d in base_durations]

        if len(self._sequence) != len(self._durations):
            logging.getLogger(__name__).warning(
                "Duration/keyframe mismatch for gesture '%s'", name
            )
            self.cancel()
            return

        self._index = 0
        self._elapsed = 0.0
        # Capture the stance once at the beginning of the gesture.  Subsequent
        # keyframes interpolate from the robot's current pose rather than this
        # entry stance.
        self._entry = [p[:] for p in self.controller.point]
        self._phase_start = [p[:] for p in self.controller.point]
        self._active = True

        # Temporarily disable locomotion and gait while the gesture runs.
        # The previous gait state is stored so it can be restored on finish.
        self._prev_gait_enabled = getattr(self.controller, "_gait_enabled", True)
        setattr(self.controller, "_locomotion_enabled", False)
        setattr(self.controller, "_gait_enabled", False)

    def cancel(self) -> None:
        """Abort the current gesture, if any, and re-enable locomotion."""
        self._active = False
        self._sequence = []
        self._durations = []
        self._index = 0
        self._elapsed = 0.0
        self._entry = None
        self._phase_start = None
        # Restore locomotion and any gait state that was active before the
        # gesture began.
        setattr(self.controller, "_locomotion_enabled", True)
        setattr(self.controller, "_gait_enabled", self._prev_gait_enabled)

    def update(self, dt: float) -> bool:
        """Advance the current gesture in a non-blocking fashion.

        The method performs linear interpolation toward the absolute target
        coordinates of the active keyframe and returns immediately so it can
        be called each iteration of the controller's main loop.

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

        duration = self._durations[self._index] if self._durations else 0.0
        target = self._sequence[self._index]
        self._elapsed += dt
        fraction = min(1.0, duration and self._elapsed / duration)

        # Interpolate from the pose at the start of this phase toward the
        # absolute target of the keyframe.
        assert self._phase_start is not None
        for leg in range(4):
            for axis in range(3):
                start_val = self._phase_start[leg][axis]
                end_val = target[leg][axis]
                self.controller.point[leg][axis] = (
                    start_val + (end_val - start_val) * fraction
                )

        if fraction >= 1.0:
            # Prepare for the next keyframe by capturing the stance once.
            self._phase_start = [p[:] for p in self.controller.point]
            self._elapsed = 0.0
            self._index += 1
            if self._index >= len(self._sequence):
                # Gesture complete
                self.cancel()
                return True
        return False
