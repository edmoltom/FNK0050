import os
import sys
import types
import unittest

# Provide a tiny ``numpy`` stub so that importing the real controller does not
# require the heavy dependency during testing.
numpy_stub = types.SimpleNamespace(
    mat=lambda x: x,
    zeros=lambda shape: [[0] * shape[1] for _ in range(shape[0])],
    array=lambda x: x,
)
sys.modules.setdefault("numpy", numpy_stub)

# Stub out hardware-dependent modules used by ``Control`` so that no external
# libraries are required for the tests.
servo_module = types.ModuleType("movement.servo")
class _StubServo:
    def setServoAngle(self, channel, angle):
        pass
    def set_servo_angle(self, channel, angle):
        pass
servo_module.Servo = _StubServo
sys.modules["movement.servo"] = servo_module

imu_module = types.ModuleType("sensing.IMU")
class _StubIMU:
    def update_imu(self):
        return 0, 0, 0, 0, 0, 0
    def average_filter(self):
        return 0, 0
imu_module.IMU = _StubIMU
sys.modules.setdefault("sensing", types.ModuleType("sensing"))
sys.modules["sensing.IMU"] = imu_module

odom_module = types.ModuleType("sensing.odometry")
class _StubOdom:
    def __init__(self, stride_gain=0.55):
        pass
    def set_heading_deg(self, val):
        pass
odom_module.Odometry = _StubOdom
sys.modules["sensing.odometry"] = odom_module

gait_module = types.ModuleType("movement.gait_cpg")
class _StubCPG:
    def __init__(self, gait):
        pass
gait_module.CPG = _StubCPG
sys.modules["movement.gait_cpg"] = gait_module

# Ensure the core package is on the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from movement.controller import Controller


class DummyPID:
    def PID_compute(self, value):
        return value


class StubController(Controller):
    """Controller subclass with stubbed hardware for testing."""
    def setup_hardware(self):
        self.imu = _StubIMU()
        self.servo = _StubServo()
        self.pid = DummyPID()
        self.odom = _StubOdom()
        self.cpg = _StubCPG("walk")
        self.log_enabled = False

    def log_current_state(self):
        pass


class ControllerCancelTest(unittest.TestCase):
    def setUp(self):
        self.controller = StubController()

    def _assert_safe_stance(self):
        expected = [
            [10, self.controller.height, 10],
            [10, self.controller.height, 10],
            [10, self.controller.height, -10],
            [10, self.controller.height, -10],
        ]
        for leg in range(4):
            for axis in range(3):
                self.assertAlmostEqual(
                    self.controller.point[leg][axis], expected[leg][axis], places=3
                )

    def test_cancel_returns_safe_stance(self):
        self.controller.gestures.start("greet")
        self.controller.update(0.1)
        self.assertTrue(self.controller.gestures.active)
        self.controller.cancel()
        self.assertFalse(self.controller.gestures.active)
        self.assertTrue(self.controller._locomotion_enabled)
        self.assertTrue(self.controller._gait_enabled)
        self._assert_safe_stance()

    def test_stop_cancels_gesture(self):
        self.controller.gestures.start("greet")
        self.controller.update(0.1)
        self.assertTrue(self.controller.gestures.active)
        self.controller.stop()
        self.assertFalse(self.controller.gestures.active)
        self._assert_safe_stance()

    def test_relax_cancels_gesture(self):
        self.controller.gestures.start("greet")
        self.controller.update(0.1)
        self.assertTrue(self.controller.gestures.active)
        self.controller.relax()
        self.assertFalse(self.controller.gestures.active)
        self._assert_safe_stance()

    def test_gait_resumes_after_completion(self):
        self.controller.gestures.start("greet")
        # Gesture should disable gait
        self.assertFalse(self.controller._gait_enabled)
        # Run until the gesture finishes
        while self.controller.gestures.active:
            self.controller.update(1.0)
        # Gait should be restored after completion
        self.assertTrue(self.controller._gait_enabled)


if __name__ == "__main__":
    unittest.main()
