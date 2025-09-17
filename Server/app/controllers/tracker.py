"""Generic object tracking helpers used by high level controllers.

This module provides a light-weight :class:`ObjectTracker` abstraction that
coordinates per-axis head controllers.  Only the vertical axis is currently
implemented which mirrors the behaviour of :class:`FaceTracker` where an
exponential moving average (EMA) is used to smooth the target position.

The user story for this change requires clearing the vertical EMA whenever the
tracker loses all targets so subsequent detections start with a fresh state.
Keeping the reset logic encapsulated inside :class:`AxisYHeadController`
prevents external callers from mutating private attributes directly and keeps
the code aligned with the pattern already used by ``FaceTracker``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Dict, Optional, Tuple


def _select_largest_box(targets: Sequence[Dict[str, float]]) -> Optional[Dict[str, float]]:
    """Return the target with the largest area.

    Parameters
    ----------
    targets:
        Iterable of bounding boxes containing ``x``, ``y``, ``w`` and ``h``
        values.  Missing keys are treated as ``0`` which results in a zero-area
        box and therefore ignored when there are valid candidates.
    """

    if not targets:
        return None
    return max(
        targets,
        key=lambda box: float(box.get("w", 0.0)) * float(box.get("h", 0.0)),
    )


class AxisYHeadController:
    """Vertical head controller with exponential smoothing.

    The controller keeps an EMA of the detected target's vertical centre.  This
    mirrors the implementation inside :class:`FaceTracker` so both controllers
    react in the same way when re-acquiring a face.  The EMA is reset via
    :meth:`reset` which is invoked by :class:`ObjectTracker` whenever no targets
    are detected.
    """

    def __init__(self, *, ema_alpha: float = 0.2) -> None:
        self.ema_alpha = float(ema_alpha)
        self._ema_center: Optional[float] = None

    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Reset the EMA state so the next detection starts fresh."""

        self._ema_center = None

    # ------------------------------------------------------------------
    def update(
        self,
        target: Optional[Dict[str, float]],
        space: Tuple[float, float],
    ) -> Optional[float]:
        """Update the EMA with ``target`` information.

        Parameters
        ----------
        target:
            Detected bounding box expressed as a mapping with ``x``, ``y``,
            ``w`` and ``h`` entries.  When ``None`` the controller simply
            returns ``None`` and leaves the EMA untouched.  Callers are
            expected to invoke :meth:`reset` when no detections are present.
        space:
            Tuple containing the frame width and height in pixels.

        Returns
        -------
        Optional[float]
            Normalised error of the EMA centre relative to the image centre, or
            ``None`` when the computation cannot be performed.
        """

        if not target or len(space) < 2:
            return None

        space_h = float(space[1])
        if space_h <= 0.0:
            return None

        y = float(target.get("y", 0.0))
        h = float(target.get("h", 0.0))
        face_center_y = y + h / 2.0

        # Reinitialise the EMA whenever a new face is observed.  This mirrors
        # ``FaceTracker.update`` where the EMA is set to the first observation
        # before smoothing subsequent frames.
        if self._ema_center is None:
            self._ema_center = face_center_y
        else:
            alpha = self.ema_alpha
            self._ema_center = alpha * face_center_y + (1.0 - alpha) * self._ema_center

        mid = space_h / 2.0
        if mid <= 0.0:
            return None
        return (self._ema_center - mid) / mid


class ObjectTracker:
    """High level helper coordinating per-axis head controllers."""

    def __init__(self, *, y_controller: Optional[AxisYHeadController] = None) -> None:
        self.y = y_controller or AxisYHeadController()
        self._hit_count = 0
        self._miss_count = 0

    # ------------------------------------------------------------------
    def update(self, result: Optional[Dict[str, object]], dt: float) -> None:
        """Update internal state using the detection ``result``.

        Parameters
        ----------
        result:
            Dictionary returned by a vision detector.  Expected keys are
            ``"targets"`` containing a sequence of bounding boxes and ``"space"``
            describing the frame size.  Missing keys are handled gracefully.
        dt:
            Time step since the previous update (currently unused but kept for
            signature parity with other controllers).
        """

        del dt  # Unused for now but kept for API compatibility.

        targets: Iterable[Dict[str, float]] | None
        if result is None:
            targets = None
        else:
            raw = result.get("targets")  # type: ignore[assignment]
            if isinstance(raw, Iterable) and not isinstance(raw, (bytes, str)):
                targets = [t for t in raw if isinstance(t, dict)]
            else:
                targets = None

        if not targets:
            self._hit_count = 0
            self._miss_count += 1
            # Clear the vertical EMA so the next detection starts fresh.
            self.y.reset()
            return

        self._miss_count = 0
        self._hit_count += 1

        target = _select_largest_box(targets)
        if target is None:
            return

        space = result.get("space") if result else None
        if not isinstance(space, (tuple, list)):
            return
        space_tuple: Tuple[float, float]
        if len(space) >= 2:
            space_tuple = (float(space[0]), float(space[1]))
        else:
            return

        self.y.update(target, space_tuple)

