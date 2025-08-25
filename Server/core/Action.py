"""High level behavioural actions for the quadruped robot."""

import threading
import time

from Control import Control
from movement.servo import Servo


class Action:
    """Simple finite-state machine mapping commands to robot motions.

    The class owns a :class:`Control` instance and a servo driver.  Public
    methods update the current ``state`` which is then executed by a
    background thread.  Each state delegates to the corresponding method in
    :class:`Control` and resets back to ``idle`` once the action completes.
    """

    def __init__(self):
        """Initialise hardware helpers and spawn the FSM thread."""
        self.servo = Servo()
        self.control = Control()
        self.max_speed = self.control.MAX_SPEED_LIMIT
        self.current_speed = 0
        self.servo.setServoAngle(15, 90)
        self.start_fsm()

    def start_fsm(self):
        """Start the background finite-state-machine thread."""
        self.state = 'idle'
        self._fsm_thread = threading.Thread(target=self._fsm_loop)
        # Daemon thread so that it exits when the main program finishes
        self._fsm_thread.daemon = True
        self._fsm_thread.start()

    def _fsm_loop(self):
        while True:
            if self.state == 'idle':
                self.control.stop_requested = True
                #self.control.relax()
                pass
                
            elif self.state == 'walking_forward':
                self.control.start_logging("walking_forward_log.csv")
                try:
                    self.control.speed = self.current_speed
                    self.control.forWard()
                finally:
                    self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'walking_backward':
                self.control.start_logging("walking_backward_log.csv")
                try:
                    self.control.speed = self.current_speed
                    self.control.backWard()
                finally:
                    self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'turning_right':
                self.control.start_logging("turning_right_log.csv")
                try:
                    self.control.speed = self.current_speed
                    self.control.turnRight()
                finally:
                    self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'turning_left':
                self.control.start_logging("turning_left_log.csv")
                try:
                    self.control.speed = self.current_speed
                    self.control.turnLeft()
                finally:
                    self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'step_right':
                self.control.start_logging("step_right_log.csv")
                try:
                    self.control.speed = self.current_speed
                    self.control.stepRight()
                finally:
                    self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'step_left':
                self.control.start_logging("step_left_log.csv")
                try:
                    self.control.speed = self.current_speed
                    self.control.stepLeft()
                finally:
                    self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'relax':
                # Drop all torque so the robot limbs become compliant
                self.control.relax(True)
                self.state = 'idle'

            elif self.state == 'greeting':
                self.hello()
                self.state = 'idle'

            time.sleep(0.1)
    
    def hello(self):
        """Perform a friendly waving motion using the front-right leg."""
        # Move all feet to initial pose
        xyz = [[-20, 120, -40], [50, 105, 0], [50, 105, 0], [0, 120, 0]]
        for i in range(4):
            xyz[i][0] = (xyz[i][0] - self.control.point[i][0]) / 30
            xyz[i][1] = (xyz[i][1] - self.control.point[i][1]) / 30
            xyz[i][2] = (xyz[i][2] - self.control.point[i][2]) / 30
        for _ in range(30):
            for i in range(4):
                self.control.point[i][0] += xyz[i][0]
                self.control.point[i][1] += xyz[i][1]
                self.control.point[i][2] += xyz[i][2]
            self.control.run()
            time.sleep(0.02)

        # Raise front-right leg for wave
        x3 = (80 - self.control.point[3][0]) / 30
        y3 = (23 - self.control.point[3][1]) / 30
        z3 = (0 - self.control.point[3][2]) / 30
        for _ in range(30):
            self.control.point[3][0] += x3
            self.control.point[3][1] += y3
            self.control.point[3][2] += z3
            self.control.run()
            time.sleep(0.01)

        # Servo oscillation to simulate waving gesture
        for _ in range(2):
            for angle in range(92, 120, 1):
                self.servo.setServoAngle(11, angle)
                time.sleep(0.01)
            for angle in range(120, 60, -1):
                self.servo.setServoAngle(11, angle)
                time.sleep(0.01)
            for angle in range(60, 92, 1):
                self.servo.setServoAngle(11, angle)
                time.sleep(0.01)

        # Return to neutral stance
        xyz = [[55, 78, 0], [55, 78, 0], [55, 78, 0], [55, 78, 0]]
        for i in range(4):
            xyz[i][0] = (xyz[i][0] - self.control.point[i][0]) / 30
            xyz[i][1] = (xyz[i][1] - self.control.point[i][1]) / 30
            xyz[i][2] = (xyz[i][2] - self.control.point[i][2]) / 30
        for _ in range(30):
            for i in range(4):
                self.control.point[i][0] += xyz[i][0]
                self.control.point[i][1] += xyz[i][1]
                self.control.point[i][2] += xyz[i][2]
            self.control.run()
            time.sleep(0.02)

    def stand_up(self):
        """Raise the robot to a standing pose."""
        self.control.speed = 2
        # upAndDown manipulates body height; parameter is extra height
        self.control.upAndDown(10)
        
if __name__=='__main__':
    pass
