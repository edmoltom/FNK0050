import sys
import time
import types
from pathlib import Path

# Stub numpy to satisfy movement.posture imports
sys.modules['numpy'] = types.SimpleNamespace()

# Create dummy hardware module before importing controller
class DummyServo:
    def __init__(self) -> None:
        self.commands = []

    def set_servo_angle(self, ch, ang):
        self.commands.append((ch, ang))

    def setServoAngle(self, ch, ang):
        self.set_servo_angle(ch, ang)


class DummyCPG:
    def __init__(self) -> None:
        self.phi = [0.0]
        self.duty_cur = 0.0
        self.amp_xy_cur = 0.0
        self.amp_z_cur = 0.0

    def update(self, dt):
        return [0.0, 0.5, 1.0, 1.5]

    def foot_position(self, *args, **kwargs):
        return 0.0, 0.0

    def set_velocity(self, vx, vy, wz):
        pass


class DummyHardware:
    def __init__(self) -> None:
        self.cpg = DummyCPG()
        self.servo = DummyServo()
        self.imu = None
        self.odom = None

    def calibration(self, point, angle):
        pass

    def apply_angles(self, angle):
        self.last_angles = angle

    def relax(self):
        pass

# Inject stub module
hardware_mod = types.SimpleNamespace(Hardware=DummyHardware)
sys.modules['movement.hardware'] = hardware_mod

# Ensure movement package is importable
sys.path.append(str(Path(__file__).resolve().parents[1] / 'Server' / 'core'))

from movement.controller import MovementController, GreetCmd  # type: ignore


def test_greet_starts_gesture_thread():
    ctrl = MovementController(hardware=DummyHardware())
    ctrl.queue.put(GreetCmd())
    ctrl.tick(0.01)
    time.sleep(0.05)
    assert ctrl.gestures.is_playing()
    ctrl.gestures.stop()
