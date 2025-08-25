"""Asynchronous CSV logger for movement related state.

This module provides a minimal :class:`MovementLogger` that can be used by
the movement controller to persist state information without blocking the
real‑time control loop.  Logging happens on a background thread and an
optional list of *odometry hooks* can be supplied.  These hooks receive the
raw logging data and may update the odometry object before the row is
written.

The logger exposes three non blocking methods:

``start(file: Path)``
    Start logging to ``file``.  A CSV header is written and the background
    worker thread is launched.

``stop()``
    Stop logging and close the file handle.  Any pending log entries are
    flushed before returning.

``log_state(timestamp, imu, leg_points, odom)``
    Queue one state sample for logging.  The call returns immediately and is
    safe to invoke from time critical code paths.
"""

from __future__ import annotations

import math
import threading
from pathlib import Path
from queue import Empty, Queue
from typing import Callable, Iterable, List, Optional, Sequence, TextIO


OdometryHook = Callable[[float, Sequence[Sequence[float]], object], None]


class MovementLogger:
    """CSV based logger used by the movement controller.

    Parameters
    ----------
    odom_hooks:
        Optional iterable of callables executed for every queued sample.  The
        callables receive ``(timestamp, leg_points, odom)`` and may mutate the
        ``odom`` object (for example to update its internal estimate).  Any
        exception raised by a hook is swallowed to keep logging robust.
    """

    def __init__(self, odom_hooks: Optional[Iterable[OdometryHook]] = None) -> None:
        self._fh: Optional[TextIO] = None
        self._queue: "Queue[tuple[float, object, List[List[float]], object]]" = Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()
        self._step = 0
        self._odom_hooks: List[OdometryHook] = list(odom_hooks or [])
        self._prev_yaw: Optional[float] = None
        self._prev_t: Optional[float] = None

    # ------------------------------------------------------------------
    @property
    def active(self) -> bool:
        """Return ``True`` if logging is currently active."""

        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    def add_odometry_hook(self, hook: OdometryHook) -> None:
        """Register an additional odometry hook."""

        self._odom_hooks.append(hook)

    # ------------------------------------------------------------------
    def start(self, file: Path) -> None:
        """Start logging to ``file``.

        The method returns immediately after spawning the worker thread.
        """

        if self.active:
            return
        self._fh = file.open("w", encoding="utf-8")
        header = [
            "timestamp",
            "step",
            "roll",
            "pitch",
            "yaw",
            "accel_x",
            "accel_y",
            "accel_z",
            "fl_x",
            "fl_y",
            "fl_z",
            "rl_x",
            "rl_y",
            "rl_z",
            "rr_x",
            "rr_y",
            "rr_z",
            "fr_x",
            "fr_y",
            "fr_z",
            "yaw_rate_dps",
            "is_stance",
            "odom_x",
            "odom_y",
            "odom_theta_deg",
        ]
        self._fh.write(",".join(header) + "\n")
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Stop logging and close the file handle."""

        if not self.active:
            return
        self._stop_evt.set()
        if self._thread:
            self._thread.join()
        self._thread = None
        if self._fh:
            self._fh.close()
        self._fh = None
        self._prev_yaw = None
        self._prev_t = None
        self._step = 0

    # ------------------------------------------------------------------
    def log_state(
        self,
        timestamp: float,
        imu: object,
        leg_points: Sequence[Sequence[float]],
        odom: object,
    ) -> None:
        """Queue a state sample for logging.

        All heavy work is deferred to a background thread.  If logging is not
        active the call becomes a no-op.
        """

        if not self.active:
            return
        # Make a cheap copy of leg_points to avoid race conditions.
        lp_copy = [list(p) for p in leg_points]
        self._queue.put((timestamp, imu, lp_copy, odom))

    # ------------------------------------------------------------------
    def _worker(self) -> None:
        """Background thread consuming queued samples."""

        while not self._stop_evt.is_set() or not self._queue.empty():
            try:
                timestamp, imu, leg_points, odom = self._queue.get(timeout=0.1)
            except Empty:
                continue

            # Obtain orientation and acceleration from IMU.
            pitch, roll, yaw, ax, ay, az = imu.update_imu()

            # Yaw rate (deg/s)
            if self._prev_yaw is None:
                yaw_rate = 0.0
            else:
                dt = max(1e-3, timestamp - (self._prev_t or timestamp))
                dyaw = (yaw - self._prev_yaw + 180) % 360 - 180
                yaw_rate = dyaw / dt
            self._prev_yaw, self._prev_t = yaw, timestamp

            # Execute odometry hooks if any
            for hook in self._odom_hooks:
                try:
                    hook(timestamp, leg_points, odom)
                except Exception:
                    pass

            # Basic stance detection: leg 0 close to ground
            is_stance = int(leg_points[0][2] <= 0.0)

            row = [
                f"{timestamp:.6f}",
                self._step,
                f"{roll:.2f}",
                f"{pitch:.2f}",
                f"{yaw:.2f}",
                f"{ax:.4f}",
                f"{ay:.4f}",
                f"{az:.4f}",
                *[f"{coord:.2f}" for leg in leg_points for coord in leg],
                f"{yaw_rate:.2f}",
                is_stance,
                f"{getattr(odom, 'x', 0.0):.2f}",
                f"{getattr(odom, 'y', 0.0):.2f}",
                f"{math.degrees(getattr(odom, 'theta', 0.0)):.2f}",
            ]

            if self._fh:
                self._fh.write(",".join(map(str, row)) + "\n")
                self._fh.flush()
            self._step += 1


__all__ = ["MovementLogger"]

