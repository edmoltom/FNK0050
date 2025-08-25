"""Low level hardware helpers for the quadruped robot."""
from __future__ import annotations

from typing import List

from .kinematics import coordinate_to_angle, clamp
from . import data
from .servo import Servo
from .gait_cpg import CPG
from ..sensing.IMU import IMU
from ..sensing.odometry import Odometry
from ..PID import Incremental_PID


class Hardware:
    """Bundle of devices used by the movement controller."""

    def __init__(self) -> None:
        self.setup_hardware()
        self.load_calibration()

    # ------------------------------------------------------------------
    def setup_hardware(self) -> None:
        self.imu = IMU()
        self.servo = Servo()
        self.pid = Incremental_PID(0.5, 0.0, 0.0025)
        self.odom = Odometry(stride_gain=0.55)
        self.cpg = CPG("walk")

    # ------------------------------------------------------------------
    def load_calibration(self) -> None:
        self.calibration_point = data.read_from_txt("point")
        self.calibration_angle = [[0.0, 0.0, 0.0] for _ in range(4)]

    # ------------------------------------------------------------------
    def calibration(self, point: List[List[float]], angle: List[List[float]]) -> None:
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
    def apply_calibration_to_angles(self, angle: List[List[float]]) -> None:
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
    def send_angles_to_servos(self, angle: List[List[float]]) -> None:
        for i in range(2):
            self.servo.setServoAngle(4 + i * 3, angle[i][0])
            self.servo.setServoAngle(3 + i * 3, angle[i][1])
            self.servo.setServoAngle(2 + i * 3, angle[i][2])

            self.servo.setServoAngle(8 + i * 3, angle[i + 2][0])
            self.servo.setServoAngle(9 + i * 3, angle[i + 2][1])
            self.servo.setServoAngle(10 + i * 3, angle[i + 2][2])
