"""Light‑weight logging helpers for movement related data."""
from __future__ import annotations

import math
import time
from typing import Iterable, Optional, TextIO


class MovementLogger:
    """CSV based logger used by the movement controller.

    The logger does not depend on the concrete controller
    implementation; instead :meth:`log_current_state` expects an object
    that exposes the minimal set of attributes that the historic
    ``Control`` class used.
    """

    def __init__(self) -> None:
        self._fh: Optional[TextIO] = None
        self._step = 0

    # ------------------------------------------------------------------
    def start_logging(self, filename: str = "empty.csv") -> None:
        """Open ``filename`` for writing and emit a CSV header."""
        self._fh = open(filename, "w")
        header: Iterable[str] = [
            "timestamp", "step", "roll", "pitch", "yaw",
            "accel_x", "accel_y", "accel_z",
            "fl_x", "fl_y", "fl_z", "rl_x", "rl_y", "rl_z",
            "rr_x", "rr_y", "rr_z", "fr_x", "fr_y", "fr_z",
            "yaw_rate_dps", "is_stance", "odom_x", "odom_y", "odom_theta_deg",
        ]
        self._fh.write(",".join(header) + "\n")
        self._step = 0

    # ------------------------------------------------------------------
    def stop_logging(self) -> None:
        """Close the file handle if logging was active."""
        if self._fh:
            self._fh.close()
            self._fh = None

    # ------------------------------------------------------------------
    def log_current_state(self, ctl: object) -> None:
        """Append one row of state values to the CSV file.

        ``ctl`` is expected to expose ``imu``, ``odom`` and ``point``
        attributes as well as a ``_gait_angle`` and the smoothing state
        ``_yr``.  This loose duck‑typing keeps the logger reusable and
        easy to test.
        """
        if not self._fh:
            return

        timestamp = time.time()
        pitch, roll, yaw, accel_x, accel_y, accel_z = ctl.imu.update_imu()

        # Compute angular velocity (yaw_rate) in deg/s
        if getattr(ctl, "_prev_yaw", None) is None:
            yaw_rate = 0.0
        else:
            dt = max(1e-3, timestamp - ctl._prev_t)
            dyaw = (yaw - ctl._prev_yaw + 180) % 360 - 180
            yaw_rate = dyaw / dt
        ctl._prev_yaw, ctl._prev_t = yaw, timestamp
        ctl._yr = 0.8 * getattr(ctl, "_yr", 0.0) + 0.2 * yaw_rate

        # Update heading for odometry
        ctl.odom.set_heading_deg(yaw)

        phase0 = getattr(ctl, "_last_phases", [0.0])[0]
        duty = getattr(ctl, "_last_duty", 0.75)
        is_stance = (phase0 <= duty) and (abs(ctl._yr) < 3.0)

        if not ctl.odom.zupt(is_stance, ctl._yr):
            ctl.odom.tick_gait(ctl._gait_angle, ctl.step_length)

        data = [
            timestamp, self._step,
            f"{roll:.2f}", f"{pitch:.2f}", f"{yaw:.2f}",
            f"{accel_x:.4f}", f"{accel_y:.4f}", f"{accel_z:.4f}",
            *[f"{coord:.2f}" for leg in ctl.point for coord in leg],
            f"{ctl._yr:.2f}", int(is_stance),
            f"{ctl.odom.x:.2f}", f"{ctl.odom.y:.2f}",
            f"{math.degrees(ctl.odom.theta):.2f}",
        ]
        self._fh.write(",".join(map(str, data)) + "\n")
        self._step += 1
