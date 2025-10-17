import time
import logging
from core.sensing.IMU import IMU
from core.sensing.odometry import Odometry

logger = logging.getLogger(__name__)


class SensorController:
    """Manages physical sensors (IMU, Odometry) and exposes structured packets."""

    def __init__(self):
        self.imu = IMU()
        self.odom = Odometry()
        logger.info("[SENSORS] Controller initialized with IMU and Odometry")

    def get_imu_packet(self) -> dict:
        """Return latest IMU reading formatted for the proprioceptive pipeline."""
        pitch, roll, yaw, ax, ay, az = self.imu.update_imu()
        return {
            "sensor": "imu",
            "timestamp": time.time(),
            "type": "relative",
            "data": {"pitch": pitch, "roll": roll, "yaw": yaw, "ax": ax, "ay": ay, "az": az},
            "confidence": 1.0,
        }

    def get_odometry_packet(self) -> dict:
        """Return latest Odometry reading formatted for the proprioceptive pipeline."""
        return {
            "sensor": "odometry",
            "timestamp": time.time(),
            "type": "relative",
            "data": {"x": self.odom.x, "y": self.odom.y, "theta": self.odom.theta},
            "confidence": 0.9,
        }
