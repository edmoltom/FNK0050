 # -*- coding: utf-8 -*-
import time
import os
import math
import smbus
import copy
import threading
from IMU import *
from PID import *
import numpy as np
from Servo import *
from Command import COMMAND as cmd

class Control:

    FL, RL, RR, FR = 0, 1, 2, 3
    X, Y, Z = 0, 1, 2
    MAX_SPEED_LIMIT = 200
    MIN_SPEED_LIMIT = 20

    def __init__(self):
        self.setup_hardware()
        self.setup_state()
        self.load_calibration()
        self.calibration()
        self.relax(True)

    def setup_hardware(self):
        self.imu = IMU()
        self.servo = Servo()
        self.pid = Incremental_PID(0.5, 0.0, 0.0025)

    def setup_state(self):
        self.speed = self.MIN_SPEED_LIMIT
        self.height = 99
        self.step_height = 10
        self.step_length = 15
        self.order = ['','','','','']
        self.point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
        self.angle = [[90,0,0],[90,0,0],[90,0,0],[90,0,0]]
        self.calibration_angle = [[0,0,0],[0,0,0],[0,0,0],[0,0,0]]
        self.stop_requested = False
        self.relax_flag = True
        self.balance_flag = False
        self.attitude_flag = False
        
    def start_logging(self, filename="empty.csv"):
        self.logfile = open(filename, "w")
        header = [
            "timestamp", "step", "roll", "pitch", "yaw",
            "accel_x", "accel_y", "accel_z",
            "fl_x", "fl_y", "fl_z",
            "rl_x", "rl_y", "rl_z",
            "rr_x", "rr_y", "rr_z",
            "fr_x", "fr_y", "fr_z"

        ]
        self.logfile.write(",".join(header) + "\n")
        self.log_enabled = True
        self.log_step = 0
    
    def stop_logging(self):
        if hasattr(self, 'logfile') and self.logfile:
            self.logfile.close()
            self.logfile = None
            self.log_enabled = False
    
    def readFromTxt(self,filename):
        base_path = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_path, filename + ".txt")
        file1 = open(filepath, "r")
        list_row = file1.readlines()
        list_source = []
        for i in range(len(list_row)):
            column_list = list_row[i].strip().split("\t")
            list_source.append(column_list)
        for i in range(len(list_source)):
            for j in range(len(list_source[i])):
                list_source[i][j] = int(list_source[i][j])
        file1.close()
        return list_source

    def saveToTxt(self,list, filename):
        base_path = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_path, filename + ".txt")
        file2 = open(filepath, 'w')
        for i in range(len(list)):
            for j in range(len(list[i])):
                file2.write(str(list[i][j]))
                file2.write('\t')
            file2.write('\n')
        file2.close()
        
    def coordinateToAngle(self,x,y,z,l1=23,l2=55,l3=55):
        a=math.pi/2-math.atan2(z,y)
        x_3=0
        x_4=l1*math.sin(a)
        x_5=l1*math.cos(a)
        l23=math.sqrt((z-x_5)**2+(y-x_4)**2+(x-x_3)**2)
        w=(x-x_3)/l23
        v=(l2*l2+l23*l23-l3*l3)/(2*l2*l23)
        b=math.asin(round(w,2))-math.acos(round(v,2))
        c=math.pi-math.acos(round((l2**2+l3**2-l23**2)/(2*l3*l2),2))
        a=round(math.degrees(a))
        b=round(math.degrees(b))
        c=round(math.degrees(c))
        return a,b,c
    
    def angleToCoordinate(self,a,b,c,l1=23,l2=55,l3=55):
        a=math.pi/180*a
        b=math.pi/180*b
        c=math.pi/180*c
        x=l3*math.sin(b+c)+l2*math.sin(b)
        y=l3*math.sin(a)*math.cos(b+c)+l2*math.sin(a)*math.cos(b)+l1*math.sin(a)
        z=l3*math.cos(a)*math.cos(b+c)+l2*math.cos(a)*math.cos(b)+l1*math.cos(a)
        return x,y,z

    def load_calibration(self):
        self.calibration_point = self.readFromTxt('point')

    def calibration(self):
        for i in range(4):
            self.calibration_angle[i][0],self.calibration_angle[i][1],self.calibration_angle[i][2]=self.coordinateToAngle(self.calibration_point[i][0],
                                                                                                                          self.calibration_point[i][1],
                                                                                                                          self.calibration_point[i][2])
        for i in range(4):
            self.angle[i][0],self.angle[i][1],self.angle[i][2]=self.coordinateToAngle(self.point[i][0],
                                                                                      self.point[i][1],
                                                                                      self.point[i][2])
        for i in range(4):
            self.calibration_angle[i][0]=self.calibration_angle[i][0]-self.angle[i][0]
            self.calibration_angle[i][1]=self.calibration_angle[i][1]-self.angle[i][1]
            self.calibration_angle[i][2]=self.calibration_angle[i][2]-self.angle[i][2]
    
    def update_angles_from_points(self):
        for i in range(4):
            self.angle[i][0], self.angle[i][1], self.angle[i][2] = self.coordinateToAngle(
                self.point[i][self.X], self.point[i][self.Y], self.point[i][self.Z])

    def apply_calibration_to_angles(self):
        for i in range(2):
            # Left legs
            self.angle[i][0] = self.restriction(self.angle[i][0] + self.calibration_angle[i][0], 0, 180)
            self.angle[i][1] = self.restriction(90 - (self.angle[i][1] + self.calibration_angle[i][1]), 0, 180)
            self.angle[i][2] = self.restriction(self.angle[i][2] + self.calibration_angle[i][2], 0, 180)

            # Right legs
            self.angle[i+2][0] = self.restriction(self.angle[i+2][0] + self.calibration_angle[i+2][0], 0, 180)
            self.angle[i+2][1] = self.restriction(90 + self.angle[i+2][1] + self.calibration_angle[i+2][1], 0, 180)
            self.angle[i+2][2] = self.restriction(180 - (self.angle[i+2][2] + self.calibration_angle[i+2][2]), 0, 180)

    def send_angles_to_servos(self):
        for i in range(2):
            # Left side servos
            self.servo.setServoAngle(4 + i*3, self.angle[i][0])
            self.servo.setServoAngle(3 + i*3, self.angle[i][1])
            self.servo.setServoAngle(2 + i*3, self.angle[i][2])

            # Right side servos
            self.servo.setServoAngle(8 + i*3, self.angle[i+2][0])
            self.servo.setServoAngle(9 + i*3, self.angle[i+2][1])
            self.servo.setServoAngle(10 + i*3, self.angle[i+2][2])

    def log_current_state(self):
        if hasattr(self, 'log_enabled') and self.log_enabled:
            timestamp = time.time()
            roll, pitch, yaw, accel_x, accel_y, accel_z = self.imu.imuUpdate()
            data = [
                timestamp,
                self.log_step,
                f"{roll:.2f}", f"{pitch:.2f}", f"{yaw:.2f}",
                f"{accel_x:.4f}", f"{accel_y:.4f}", f"{accel_z:.4f}",
                *[f"{coord:.2f}" for leg in self.point for coord in leg]
            ]
            self.logfile.write(",".join(map(str, data)) + "\n")
            self.log_step += 1        

    def run(self):
        # Uncomment the next line to measure execution time
        # start = time.monotonic()
        if self.checkPoint():
            try:
                self.update_angles_from_points()
                self.apply_calibration_to_angles()
                self.send_angles_to_servos()
                self.log_current_state()
            except Exception as e:
                print("Exception during run():", e)
        # Uncomment the next line to print execution time
        # print(f"Time: {time.monotonic() - start:.2f} s")
        else:
            print("This coordinate point is out of the active range")

    def checkPoint(self):
        flag=True
        leg_lenght=[0,0,0,0,0,0]  
        for i in range(4):
          leg_lenght[i]=math.sqrt(self.point[i][0]**2+self.point[i][1]**2+self.point[i][2]**2)
        for i in range(4         ):
          if leg_lenght[i] > 130 or leg_lenght[i] < 25:
            flag=False
        return flag
    
    def restriction(self,var,v_min,v_max):
        if var < v_min:
            return v_min
        elif var > v_max:
            return v_max
        else:
            return var            
    
    def map(self,value,fromLow,fromHigh,toLow,toHigh):
        return (toHigh-toLow)*(value-fromLow) / (fromHigh-fromLow) + toLow
    
    def set_leg_position(self, leg, x, y, z):
        self.point[leg][self.X] = x
        self.point[leg][self.Y] = y
        self.point[leg][self.Z] = z

    def changeCoordinates(self, move_order, X1=0, Y1=96, Z1=0, X2=0, Y2=96, Z2=0, pos=np.mat(np.zeros((3, 4)))):
        """
        Update self.point coordinates depending on movement type.
        This will modify the leg positions for different movement behaviors.
        """

        if move_order == 'turnLeft':
            for i in range(2):
                leg1 = 2 * i
                leg2 = 1 + 2 * i
                x1 = ((-1)**(1+i)) * X1 + 10
                y1 = Y1
                z1 = ((-1)**i) * Z1 + ((-1)**i) * 10

                x2 = ((-1)**(1+i)) * X2 + 10
                y2 = Y2
                z2 = ((-1)**(1+i)) * Z2 + ((-1)**i) * 10

                self.set_leg_position(leg1, x1, y1, z1)
                self.set_leg_position(leg2, x2, y2, z2)

        elif move_order == 'turnRight':
            for i in range(2):
                leg1 = 2 * i
                leg2 = 1 + 2 * i
                x1 = ((-1)**i) * X1 + 10
                y1 = Y1
                z1 = ((-1)**(1+i)) * Z1 + ((-1)**i) * 10

                x2 = ((-1)**i) * X2 + 10
                y2 = Y2
                z2 = ((-1)**i) * Z2 + ((-1)**i) * 10

                self.set_leg_position(leg1, x1, y1, z1)
                self.set_leg_position(leg2, x2, y2, z2)

        elif move_order in ['height', 'horizon']:
            for i in range(2):
                self.set_leg_position(3*i, X1 + 10, Y1, self.point[3*i][self.Z])
                self.set_leg_position(1+i, X2 + 10, Y2, self.point[1+i][self.Z])

        elif move_order == 'Attitude Angle':
            for i in range(2):
                self.set_leg_position(3-i,
                                      pos[0,1+2*i] + 10,
                                      pos[2,1+2*i],
                                      pos[1,1+2*i])
                self.set_leg_position(i,
                                      pos[0,2*i] + 10,
                                      pos[2,2*i],
                                      pos[1,2*i])

        else:
            for i in range(2):
                self.set_leg_position(i*2, X1 + 10, Y1, Z1 + ((-1)**i) * 10)
                self.set_leg_position(i*2+1, X2 + 10, Y2, Z2 + ((-1)**i) * 10)

        self.run()
    
    def wait_for_next_tick(self, last_tick, tick_time):
        next_tick = last_tick + tick_time
        now = time.monotonic()
        time.sleep(max(0, next_tick - now))
        return next_tick

    def clamp_speed(self, min_val=MIN_SPEED_LIMIT, max_val=MAX_SPEED_LIMIT):
        self.speed = max(min_val, min(self.speed, max_val))

    def step_move(self, axis: str, mode: str, direction: str):
        # direction: 'positive' or 'negative'
        # - for axis 'X': 'positive' = forward, 'negative' = backward
        # - for axis 'Z': 'positive' = left,    'negative' = right
        self.clamp_speed()
        tick_time = 1.0 / self.speed
        tick = time.monotonic()

        angle = 90 if direction == 'positive' else 450
        end_angle = 450 if direction == 'positive' else 90
        step = 3 if direction == 'positive' else -3

        while (step > 0 and angle <= end_angle) or (step < 0 and angle >= end_angle):
            if self.stop_requested:
                break

            primary_offset = self.step_length * math.cos(math.radians(angle))
            secondary_offset = self.step_length * math.cos(math.radians(angle + 180))
            y1 = self.step_height * math.sin(math.radians(angle)) + self.height
            y2 = self.step_height * math.sin(math.radians(angle + 180)) + self.height
            y1 = min(y1, self.height)
            y2 = min(y2, self.height)

            if axis == 'X':
                self.changeCoordinates(mode, primary_offset, y1, 0, secondary_offset, y2, 0)
            elif axis == 'Z':
                self.changeCoordinates(mode, 0, y1, primary_offset, 0, y2, secondary_offset)

            angle += step
    
    def forWard(self):
        self.step_move('X', 'forWard', 'positive')

    def backWard(self):
        self.step_move('X', 'backWard', 'negative')

    def stepLeft(self):
        self.step_move('Z', 'stepLeft', 'positive')

    def stepRight(self):
        self.step_move('Z', 'stepRight', 'negative')
    
    def turn(self, mode: str):
        self.clamp_speed()
        tick_time = 1.0 / self.speed
        tick = time.monotonic()
        angle = 0
        step = 3  

        while angle <= 360:
            if self.stop_requested:
                break

            X1 = self.step_length * math.cos(math.radians(angle))
            Y1 = self.step_height * math.sin(math.radians(angle)) + self.height
            Z1 = X1  

            X2 = self.step_length * math.cos(math.radians(angle + 180))
            Y2 = self.step_height * math.sin(math.radians(angle + 180)) + self.height
            Z2 = X2

            Y1 = min(Y1, self.height)
            Y2 = min(Y2, self.height)

            self.changeCoordinates(mode, X1, Y1, Z1, X2, Y2, Z2)

            angle += step
            tick = self.wait_for_next_tick(tick, tick_time)
    
    def turnLeft(self):
        self.turn("turnLeft")

    def turnRight(self):
        self.turn("turnRight")
    
    def stop(self):
        p=[[10, self.height, 10], [10, self.height, 10], [10, self.height, -10], [10, self.height, -10]]
        for i in range(4):
            p[i][0]=(p[i][0]-self.point[i][0])/50
            p[i][1]=(p[i][1]-self.point[i][1])/50
            p[i][2]=(p[i][2]-self.point[i][2])/50
        for j in range(50):
            for i in range(4):
                self.point[i][0]+=p[i][0]
                self.point[i][1]+=p[i][1]
                self.point[i][2]+=p[i][2]
            self.run()
    
    def relax(self,flag=False):
        if flag==True:
            p=[[55, 78, 0], [55, 78, 0], [55, 78, 0], [55, 78, 0]]
            for i in range(4):
                p[i][0]=(self.point[i][0]-p[i][0])/50
                p[i][1]=(self.point[i][1]-p[i][1])/50
                p[i][2]=(self.point[i][2]-p[i][2])/50
            for j in range(1,51):
                for i in range(4):
                    self.point[i][0]-=p[i][0]
                    self.point[i][1]-=p[i][1]
                    self.point[i][2]-=p[i][2]
                self.run()
        else:
            self.stop()
    
    def upAndDown(self,var):
        self.height=var+99
        self.changeCoordinates('height',0,self.height,0,0,self.height,0)
    
    def beforeAndAfter(self,var):
        self.changeCoordinates('horizon',var,self.height,0,var,self.height,0)
    
    def attitude(self,r,p,y):
        r=self.map(int(r),-20,20,-10,10)
        p=self.map(int(p),-20,20,-10,10)
        y=self.map(int(y),-20,20,-10,10)
        pos=self.postureBalance(r,p,y,0)
        self.changeCoordinates('Attitude Angle',pos=pos)
    
    def IMU6050(self):
        self.balance_flag=True
        self.order=['','','','','']
        pos=self.postureBalance(0,0,0)
        self.changeCoordinates('Attitude Angle',pos=pos)
        time.sleep(2)
        self.imu.Error_value_accel_data,self.imu.Error_value_gyro_data=self.imu.average_filter()
        time.sleep(1)
        while True:
            r,p,y=self.imu.imuUpdate()
            r=self.pid.PID_compute(r)
            p=self.pid.PID_compute(p)
            pos=self.postureBalance(r,p,0)
            self.changeCoordinates('Attitude Angle',pos=pos)
            if  (self.order[0]==cmd.CMD_BALANCE and self.order[1]=='0')or(self.balance_flag==True and self.order[0]!=''):
                Thread_conditiona=threading.Thread(target=self.condition)
                Thread_conditiona.start()
                self.balance_flag==False
                break
    
    def postureBalance(self,r,p,y,h=1):
        b = 76
        w = 76
        l = 136
        if h!=0:
            h=self.height
        pos = np.mat([0.0,  0.0,  h ]).T 
        rpy = np.array([r,  p,  y]) * math.pi / 180 
        R, P, Y = rpy[0], rpy[1], rpy[2]
        rotx = np.mat([[ 1,       0,            0          ],
                     [ 0,       math.cos(R), -math.sin(R)],
                     [ 0,       math.sin(R),  math.cos(R)]])
        roty = np.mat([[ math.cos(P),  0,      -math.sin(P)],
                     [ 0,            1,       0          ],
                     [ math.sin(P),  0,       math.cos(P)]]) 
        rotz = np.mat([[ math.cos(Y), -math.sin(Y),  0     ],
                     [ math.sin(Y),  math.cos(Y),  0     ],
                     [ 0,            0,            1     ]])
        rot_mat = rotx * roty * rotz
        body_struc = np.mat([[ l / 2,  b / 2,  0],
                           [ l / 2, -b / 2,    0],
                           [-l / 2,  b / 2,    0],
                           [-l / 2, -b / 2,    0]]).T
        footpoint_struc = np.mat([[(l / 2),  (w / 2)+10,  self.height-h],
                                [ (l / 2), (-w / 2)-10,    self.height-h],
                                [(-l / 2),  (w / 2)+10,    self.height-h],
                                [(-l / 2), (-w / 2)-10,    self.height-h]]).T
        AB = np.mat(np.zeros((3, 4)))
        for i in range(4):
            AB[:, i] = pos + rot_mat * footpoint_struc[:, i] - body_struc[:, i]
        return (AB)
        
if __name__=='__main__':
    pass