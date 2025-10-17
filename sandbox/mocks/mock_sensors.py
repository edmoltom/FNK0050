import random
import time
import logging

logger = logging.getLogger(__name__)


class MockIMU:
    """Simulated IMU sensor generating pseudo-random orientation and acceleration values."""

    def update_imu(self):
        t = time.time()
        # small oscillations in orientation and random accelerations
        pitch = 5.0 * random.uniform(-1, 1)
        roll = 3.0 * random.uniform(-1, 1)
        yaw = (t * 10.0) % 360.0
        ax = random.uniform(-0.05, 0.05)
        ay = random.uniform(-0.05, 0.05)
        az = 9.81 + random.uniform(-0.05, 0.05)
        return (pitch, roll, yaw, ax, ay, az)


class MockOdometry:
    """Simulated odometry sensor tracking a small wandering motion."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

    def step(self, dt=0.1):
        self.x += random.uniform(-0.01, 0.01)
        self.y += random.uniform(-0.01, 0.01)
        self.theta += random.uniform(-0.01, 0.01)
        return (self.x, self.y, self.theta)
