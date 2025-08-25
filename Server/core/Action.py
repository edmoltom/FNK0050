import threading
import time

from movement.controller import Controller

class Action:

    def __init__(self):
        self.control = Controller()
        self.max_speed = self.control.MAX_SPEED_LIMIT
        self.current_speed = 0
        # Example servo initialisation routed through the controller
        self.control.set_servo_angle(15, 90)
        self.start_fsm()

    def start_fsm(self):
        self.state = 'idle'
        self._fsm_thread = threading.Thread(target=self._fsm_loop)
        self._fsm_thread.daemon = True  # will be closed with main script
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
                self.control.relax(True)
                self.state = 'idle'

            elif self.state == 'greeting':
                self.hello()
                self.state = 'idle'

            time.sleep(0.1)
    
    def hello(self):
        """Trigger the greeting gesture."""
        self.control.greet()

    def stand_up(self):
        self.control.speed = 2
        self.control.upAndDown(10)  #walking_backward height height + default (default 99)             
        
if __name__=='__main__':
    pass
