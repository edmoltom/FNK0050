import os
import sys
import unittest

# Ensure the core package is on the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from movement.gestures import Gestures


class _StubController:
    def __init__(self):
        self.point = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        self._locomotion_enabled = True

    def stop(self):
        pass


class GestureSpeedTest(unittest.TestCase):
    def setUp(self):
        self.controller = _StubController()
        self.gestures = Gestures(self.controller)

    def test_speed_scalar_scales_durations(self):
        self.gestures.start("greet", speed=2.0)
        self.assertAlmostEqual(self.gestures._durations[0], 0.3)

    def test_duration_override(self):
        custom = [1.0, 1.0, 1.0, 1.0]
        self.gestures.start("greet", durations=custom)
        self.assertEqual(self.gestures._durations, custom)


if __name__ == "__main__":
    unittest.main()
