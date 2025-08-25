"""Hardware abstraction for robot movement.

This module centralises access to low level devices such as the PCA9685
servo controller, IMU and odometry.  It also encapsulates the mapping
between logical leg joints and physical servo channels as well as the
calibration offsets for each joint.

The :class:`Hardware` class exposes two public methods used by the higher
level movement controller:

``apply_angles``
    Apply a list of joint angles to the servos taking calibration into
    account.

``relax``
    Disable all servo outputs, allowing the robot to relax.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from .kinematics import coordinate_to_angle, clamp
from .data import load_points
from .servo import Servo
from .gait_cpg import CPG
from sensing.IMU import IMU
from sensing.odometry import Odometry
from PID import Incremental_PID


class Hardware:
    """Bundle of devices used by the movement controller."""

    #: Mapping from leg index to PCA9685 channels (hip, thigh, knee)
    SERVO_MAP = (
        (4, 3, 2),   # Front-left
        (7, 6, 5),   # Rear-left
        (8, 9, 10),  # Rear-right
        (11, 12, 13) # Front-right
    )

    def __init__(self, *, imu: Optional[IMU] = None, odom: Optional[Odometry] = None) -> None:
        """Create a new hardware bundle.

        Parameters
        ----------
        imu:
            Optional IMU instance.  If ``None`` a default :class:`IMU` will be
            constructed.
        odom:
            Optional odometry instance.  If ``None`` a default
            :class:`Odometry` will be constructed.
        """
        self.setup_hardware(imu=imu, odom=odom)
        self.load_calibration()

    # ------------------------------------------------------------------
    def setup_hardware(self, *, imu: Optional[IMU] = None, odom: Optional[Odometry] = None) -> None:
        """Initialise the individual hardware components."""
        self.imu = imu or IMU()
        self.servo = Servo()
        self.pid = Incremental_PID(0.5, 0.0, 0.0025)
        self.odom = odom or Odometry(stride_gain=0.55)
        self.cpg = CPG("walk")

    # ------------------------------------------------------------------
    def load_calibration(self) -> None:
        point_file = Path(__file__).resolve().parents[1] / "point.txt"
        self.calibration_point = load_points(point_file)
        self.calibration_angle = [[0.0, 0.0, 0.0] for _ in range(4)]

    # ------------------------------------------------------------------
    def calibration(self, point: List[List[float]], angle: List[List[float]]) -> None:
        """Compute calibration offsets from reference points."""
        for i in range(4):
            self.calibration_angle[i][0], self.calibration_angle[i][1], self.calibration_angle[i][2] = coordinate_to_angle(
                self.calibration_point[i][0], self.calibration_point[i][1], self.calibration_point[i][2]
            )
        for i in range(4):
            angle[i][0], angle[i][1], angle[i][2] = coordinate_to_angle(
                point[i][0], point[i][1], point[i][2]
            )
        for i in range(4):
            self.calibration_angle[i][0] -= angle[i][0]
            self.calibration_angle[i][1] -= angle[i][1]
            self.calibration_angle[i][2] -= angle[i][2]

    # ------------------------------------------------------------------
    def _apply_calibration_to_angles(self, angle: List[List[float]]) -> None:
        for i in range(2):
            # Left legs
            angle[i][0] = clamp(angle[i][0] + self.calibration_angle[i][0], 0, 180)
            angle[i][1] = clamp(90 - (angle[i][1] + self.calibration_angle[i][1]), 0, 180)
            angle[i][2] = clamp(angle[i][2] + self.calibration_angle[i][2], 0, 180)

            # Right legs
            angle[i + 2][0] = clamp(angle[i + 2][0] + self.calibration_angle[i + 2][0], 0, 180)
            angle[i + 2][1] = clamp(90 + angle[i + 2][1] + self.calibration_angle[i + 2][1], 0, 180)
            angle[i + 2][2] = clamp(180 - (angle[i + 2][2] + self.calibration_angle[i + 2][2]), 0, 180)

    # ------------------------------------------------------------------
    def _send_angles_to_servos(self, angle: Iterable[Iterable[float]]) -> None:
        for channels, leg_angle in zip(self.SERVO_MAP, angle):
            for ch, ang in zip(channels, leg_angle):
                self.servo.set_servo_angle(ch, ang)

    # ------------------------------------------------------------------
    def apply_angles(self, angle: List[List[float]]) -> None:
        """Apply joint angles to the servos.

        The provided ``angle`` matrix is modified in place after applying the
        calibration offsets and finally dispatched to the PCA9685 driver.
        """
        self._apply_calibration_to_angles(angle)
        self._send_angles_to_servos(angle)

    # ------------------------------------------------------------------
    def relax(self) -> None:
        """Disable all servo outputs allowing the robot to relax."""
        pwm = self.servo.pwm
        for ch in range(16):
            if hasattr(pwm, "set_pwm"):
                pwm.set_pwm(ch, 0, 0)
            elif hasattr(pwm, "setPWM"):
                pwm.setPWM(ch, 0, 0)
