import math
import threading
import time

from Control import *
from Servo import *

class Action:

    def __init__(self):
        self.servo=Servo()
        self.control=Control()
        self.max_speed = self.control.MAX_SPEED_LIMIT
        self.current_speed = 0
        self.servo.setServoAngle(15,90)
        self.start_fsm()

    def start_fsm(self):
        self.state = 'idle'
        self._fsm_thread = threading.Thread(target=self._fsm_loop)
        self._fsm_thread.daemon = True  # will be closed with main script
        self._fsm_thread.start()

    def _fsm_loop(self):
        while True:
            if self.state == 'idle':
                #self.control.relax()
                pass
                
            elif self.state == 'walking_forward':
                #self.control.start_logging("walking_frodward_log.csv")
                self.control.speed = self.current_speed   
                self.control.forWard()                             
                self.state = 'idle'
                #self.control.stop_logging()

            elif self.state == 'walking_backward':
                #self.control.start_logging("walking_backward_log.csv")
                self.control.speed = self.current_speed   
                self.control.backWard()                             
                #self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'turning_right':
                #self.control.start_logging("turning_right_log.csv")
                self.control.speed = self.current_speed   
                self.control.turnRight()                             
                #self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'turning_left':
                #self.control.start_logging("turning_left_log.csv")
                self.control.speed = self.current_speed   
                self.control.turnLeft()                             
                #self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'step_right':
                #self.control.start_logging("step_right_log.csv")
                self.control.speed = self.current_speed   
                self.control.stepRight()                             
                #self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'step_left':
                #self.control.start_logging("step_left_log.csv")
                self.control.speed = self.current_speed   
                self.control.stepLeft()                             
                #self.control.stop_logging()
                self.state = 'idle'

            elif self.state == 'relax':
                self.control.relax(True)
                self.state = 'idle'

            elif self.state == 'greeting':
                self.hello()
                self.state = 'idle'

            time.sleep(0.1)
    
    def hello(self):  
        #self.control.start_logging("hello.csv")
        xyz=[[-20,120,-40],[50,105,0],[50,105,0],[0,120,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)
        x3=(80-self.control.point[3][0])/30
        y3=(23-self.control.point[3][1])/30
        z3=(0-self.control.point[3][2])/30
        for j in range(30):
            self.control.point[3][0]+=x3
            self.control.point[3][1]+=y3
            self.control.point[3][2]+=z3
            self.control.run()
            time.sleep(0.01)
        for i in range(2):
            for i in range(92,120,1):
                self.servo.setServoAngle(11,i)
                time.sleep(0.01)
            for i in range(120,60,-1):
                self.servo.setServoAngle(11,i)
                time.sleep(0.01)
            for i in range(60,92,1):
                self.servo.setServoAngle(11,i)
                time.sleep(0.01)
        xyz=[[55,78,0],[55,78,0],[55,78,0],[55,78,0]]
        for i in range(4):
            xyz[i][0]=(xyz[i][0]-self.control.point[i][0])/30
            xyz[i][1]=(xyz[i][1]-self.control.point[i][1])/30
            xyz[i][2]=(xyz[i][2]-self.control.point[i][2])/30
        for j in range(30):
            for i in range(4):
                self.control.point[i][0]+=xyz[i][0]
                self.control.point[i][1]+=xyz[i][1]
                self.control.point[i][2]+=xyz[i][2]
            self.control.run()
            time.sleep(0.02)

    def stand_up(self):
        self.control.speed = 2
        self.control.upAndDown(10)  #walking_backward height height + default (default 99)             
        
if __name__=='__main__':
    pass