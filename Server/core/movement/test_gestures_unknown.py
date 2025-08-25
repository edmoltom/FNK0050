import os
import sys
import unittest

# Ensure the core package is on the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from movement.gestures import Gestures


class _StubController:
    def __init__(self):
        self.point = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
            [10, 11, 12],
        ]
        self._locomotion_enabled = True
        self.stop_called = False

    def stop(self):
        self.stop_called = True


class UnknownGestureTest(unittest.TestCase):
    def setUp(self):
        self.controller = _StubController()
        self.gestures = Gestures(self.controller)

    def test_start_unknown_gesture(self):
        start_pose = [p[:] for p in self.controller.point]
        logger_name = Gestures.__module__
        with self.assertLogs(logger_name, level="WARNING") as cm:
            self.gestures.start("invalid")

        self.assertFalse(self.gestures.active)
        self.assertEqual(self.controller.point, start_pose)
        self.assertTrue(self.controller._locomotion_enabled)
        self.assertFalse(self.controller.stop_called)
        self.assertTrue(any("Unrecognized gesture" in msg for msg in cm.output))

    def test_supported_lists_gestures(self):
        self.assertIn("greet", self.gestures.supported())


if __name__ == "__main__":
    unittest.main()

