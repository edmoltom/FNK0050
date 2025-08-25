import time
import os
import math
from pathlib import Path
import numpy as np
from PID import Incremental_PID
from movement.servo import Servo
from movement.gait_cpg import CPG
from movement import data
from sensing.IMU import IMU
from sensing.odometry import Odometry
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
        self.odom = Odometry(stride_gain=0.55)
        self.cpg = CPG("walk")

    def setup_state(self):
        self.speed = self.MIN_SPEED_LIMIT
        self.height = 99
        self.step_height = 10
        self.step_length = 15
        self.order = ['','','','','']
        self.point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
        self.angle = [[90,0,0],[90,0,0],[90,0,0],[90,0,0]]
        self.calibration_angle = [[0,0,0],[0,0,0],[0,0,0],[0,0,0]]
        self._prev_yaw = None
        self._prev_t = None
        self._prev_t_gait = None
        self._gait_angle = 0.0
        self._yr = 0.0
        self._is_turning = False
        self._turn_dir = 0  # +1 izquierda, -1 derecha
        self._stride_dir_x = 1  # +1 = adelante, -1 = atrás, 0 = sin avance X
        self._stride_dir_z = 0  # +1 izquierda, -1 derecha
        self.stop_requested = False
        self.relax_flag = True
        self.balance_flag = False
        self.attitude_flag = False
        
    def start_logging(self, filename="empty.csv"):
        self.logfile = open(filename, "w")
        header = [
            "timestamp","step","roll","pitch","yaw","accel_x","accel_y","accel_z",
            "fl_x","fl_y","fl_z","rl_x","rl_y","rl_z","rr_x","rr_y","rr_z","fr_x","fr_y","fr_z",
            "yaw_rate_dps","is_stance","odom_x","odom_y","odom_theta_deg"
        ]
        self.logfile.write(",".join(header) + "\n")
        self.log_enabled = True
        self.log_step = 0
    
    def stop_logging(self):
        if hasattr(self, 'logfile') and self.logfile:
            self.logfile.close()
            self.logfile = None
            self.log_enabled = False
    
    def readFromTxt(self, filename):
        base_path = Path(__file__).resolve().parent
        return data.load_points(base_path / f"{filename}.txt")

    def saveToTxt(self, list, filename):
        base_path = Path(__file__).resolve().parent
        data.save_points(base_path / f"{filename}.txt", list)
        
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

            # IMU read
            pitch, roll, yaw, accel_x, accel_y, accel_z = self.imu.update_imu()

            # Compute angular velocity (yaw_rate) in deg/s
            if self._prev_yaw is None:
                yaw_rate = 0.0
            else:
                dt = max(1e-3, timestamp - self._prev_t)  # avoid division by zero
                dyaw = (yaw - self._prev_yaw + 180) % 360 - 180  # wrap to [-180, 180]
                yaw_rate = dyaw / dt

            # Store current values as "previous" for the next iteration
            self._prev_yaw, self._prev_t = yaw, timestamp

            # Low-pass filter yaw_rate to reduce noise and avoid false ZUPT
            self._yr = 0.8 * self._yr + 0.2 * yaw_rate

            # Update heading for odometry
            self.odom.set_heading_deg(yaw)

            # Fase de la pata 0 y duty actual (fallbacks por si faltan)
            phase0 = getattr(self, "_last_phases", [0.0])[0]
            duty   = getattr(self, "_last_duty", 0.75)

            # Determine stance based on gait phase and low rotation
            is_stance = (phase0 <= duty) and (abs(self._yr) < 3.0)

            # Odometry: if no ZUPT, accumulate stride-based advance
            if not self.odom.zupt(is_stance, self._yr):
                self.odom.tick_gait(self._gait_angle, self.step_length)

            # Write row to CSV
            data = [
                timestamp, self.log_step,
                f"{roll:.2f}", f"{pitch:.2f}", f"{yaw:.2f}",
                f"{accel_x:.4f}", f"{accel_y:.4f}", f"{accel_z:.4f}",
                *[f"{coord:.2f}" for leg in self.point for coord in leg],
                f"{self._yr:.2f}",          # smoothed yaw rate
                int(is_stance),             # 1 = in stance, 0 = in swing
                f"{self.odom.x:.2f}",
                f"{self.odom.y:.2f}",
                f"{math.degrees(self.odom.theta):.2f}"
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

    def changeCoordinates(self, move_order,
                        X1=0, Y1=96, Z1=0, X2=0, Y2=96, Z2=0,
                        pos=None):
        """
        Update self.point coordinates depending on movement type.
        This will modify the leg positions for different movement behaviors.
        """
        if pos is None:
            # 3x4 zero matrix (x,y,z rows; 4 legs as columns)
            pos = np.mat(np.zeros((3, 4)))

        if move_order == 'turnLeft':
            self.set_leg_position(self.FL,  -X1 + 10, Y1,  Z1 + 10)
            self.set_leg_position(self.RL,  -X2 + 10, Y2, -Z2 + 10)
            self.set_leg_position(self.RR,   X1 + 10, Y1, -Z1 - 10)
            self.set_leg_position(self.FR,   X2 + 10, Y2,  Z2 - 10)

        elif move_order == 'turnRight':
            self.set_leg_position(self.FL,  X1 + 10, Y1, -Z1 + 10)
            self.set_leg_position(self.RL,  X2 + 10, Y2,  Z2 + 10)
            self.set_leg_position(self.RR, -X1 + 10, Y1, -Z1 - 10)
            self.set_leg_position(self.FR, -X2 + 10, Y2, -Z2 - 10)

        elif move_order in ['height', 'horizon']:
            for i in range(2):
                self.set_leg_position(3*i,   X1 + 10, Y1, self.point[3*i][self.Z])
                self.set_leg_position(1 + i, X2 + 10, Y2, self.point[1 + i][self.Z])

        elif move_order == 'Attitude Angle':
            for i in range(2):
                self.set_leg_position(3 - i, pos[0, 1 + 2*i] + 10, pos[2, 1 + 2*i], pos[1, 1 + 2*i])
                self.set_leg_position(i,     pos[0, 2*i] + 10,     pos[2, 2*i],     pos[1, 2*i])

        else:
            for i in range(2):
                self.set_leg_position(i*2,   X1 + 10, Y1, Z1 + ((-1)**i) * 10)
                self.set_leg_position(i*2+1, X2 + 10, Y2, Z2 + ((-1)**i) * 10)

        self.run()
    
    def wait_for_next_tick(self, last_tick, tick_time):
        next_tick = last_tick + tick_time
        now = time.monotonic()
        time.sleep(max(0, next_tick - now))
        return next_tick

    def clamp_speed(self, min_val=None, max_val=None):
        if min_val is None: min_val = self.MIN_SPEED_LIMIT
        if max_val is None: max_val = self.MAX_SPEED_LIMIT
        self.speed = max(min_val, min(self.speed, max_val))

    def speed_scale(self):
        rng = max(1, self.MAX_SPEED_LIMIT - self.MIN_SPEED_LIMIT)
        return max(0.0, min(1.0, (self.speed - self.MIN_SPEED_LIMIT) / rng))

    def update_legs_from_cpg(self, dt):
        
        Z_BASE = [10, 10, -10, -10]  # FL, RL, RR, FR

        phases = self.cpg.update(dt)
        self._last_phases = phases              # fases [0..1) por pata
        self._last_duty   = getattr(self.cpg, "duty_cur", self.cpg.duty)
        self._gait_angle = phases[0] * 360.0  # proxy para ZUPT/odometría

        # stride/lift con rampa (mm)
        stride_len  = int(30 * min(1.0, self.cpg.amp_xy_cur))   
        lift_height = int(12 * min(1.0, self.cpg.amp_z_cur))    
        
        base_y = self.height
        sx = getattr(self, "_stride_dir_x", 0)
        sz = getattr(self, "_stride_dir_z", 0)

        if getattr(self, "_is_turning", False) and getattr(self, "_turn_dir", 0) != 0:
            tdir = 1 if getattr(self, "_turn_dir", 0) >= 0 else -1  # +1 izq, -1 der
            for i, ph in enumerate(phases):
                s_m, lift_m = self.cpg.foot_position(ph, self.cpg.duty_cur,
                                                    stride_len=stride_len/1000.0,
                                                    lift_height=lift_height/1000.0)
                s_mm, lift_mm = s_m*1000.0, lift_m*1000.0
                # signos por pata para rotar (patrón tipo tu antiguo turn*)
                x_mult = [-1, -1, +1, +1][i] * tdir
                z_mult = [+1, -1, -1, +1][i] * tdir

                X = 10 + x_mult * s_mm
                Y = base_y - 0.45 * lift_mm
                Z = Z_BASE[i] + z_mult * s_mm 
                self.set_leg_position(i, X, Y, Z)
            return  # salimos: no seguimos a ramas X/Z

        # Elegimos eje: prioridad X; si no, Z; si ninguno, quieto
        if sx != 0:
            
            stride_signed = stride_len * sx
            for i, ph in enumerate(phases):
                s_m, lift_m = self.cpg.foot_position(
                    ph, self.cpg.duty_cur,
                    stride_len=stride_signed/1000.0,
                    lift_height=lift_height/1000.0
                )
                s_mm, lift_mm = s_m*1000.0, lift_m*1000.0
                X = s_mm + 10
                Y = base_y - 0.45 * lift_mm
                Z = Z_BASE[i]         # lateral base
                self.set_leg_position(i, X, Y, Z)

        elif sz != 0:
            stride_signed = stride_len * sz
            for i, ph in enumerate(phases):
                s_m, lift_m = self.cpg.foot_position(ph, self.cpg.duty_cur,
                                                    stride_len=stride_signed/1000.0,
                                                    lift_height=lift_height/1000.0)
                s_mm, lift_mm = s_m*1000.0, lift_m*1000.0
                X = 10                        # sin avance longitudinal
                Y = base_y - 0.45 * lift_mm
                Z = Z_BASE[i] + s_mm   # zancada lateral
                self.set_leg_position(i, X, Y, Z)
        else:
            # Neutro (por si acaso)
            for i in range(4):
                self.set_leg_position(i, 10, base_y, Z_BASE[i])


    def step_move(self, axis: str, mode: str, direction: str, cycles: int = 1):

        self.clamp_speed()
        tick_time = 1.0 / self.speed
        tick = time.monotonic()
        scale = self.speed_scale()

        self._is_turning = False
        self._turn_dir = 0
        
        if axis == 'X':
            vx, vy, wz = (1.0 if direction=='positive' else -1.0)*scale, 0.0, 0.0
            self._stride_dir_x, self._stride_dir_z = (1 if direction=='positive' else -1), 0
        elif axis == 'Z':
            vx, vy, wz = 0.0, (1.0 if direction=='positive' else -1.0)*scale, 0.0
            self._stride_dir_x, self._stride_dir_z = 0, (1 if direction=='positive' else -1)
        else:  
            vx, vy, wz = 0.0, 0.0, (1.0 if direction=='positive' else -1.0)*scale
            self._stride_dir_x = 0
            self._stride_dir_z = 0
            self._is_turning = True
            self._turn_dir = 1 if direction=='positive' else -1

        self.cpg.set_velocity(vx, vy, wz)

        # Bucle limitado por nº de ciclos del CPG
        self.stop_requested = False
        self._prev_t_gait = time.monotonic()
        prev_phase = self.cpg.phi[0]    # fase base del oscilador (sin offset)
        done = 0

        while not self.stop_requested and done < cycles:
            now = time.monotonic()
            dt = now - self._prev_t_gait
            self._prev_t_gait = now

            self.update_legs_from_cpg(dt)

            self.run()

            # Contar ciclo cuando la fase “envuelve”
            phase0 = self.cpg.phi[0]
            if phase0 < prev_phase:
                done += 1
            prev_phase = phase0

            tick = self.wait_for_next_tick(tick, tick_time)
    
    def forWard(self):
        self.step_move('X', 'forWard', 'positive')

    def backWard(self):
        self.step_move('X', 'backWard', 'negative')

    def stepLeft(self):
        self.step_move('Z', 'stepLeft', 'positive')

    def stepRight(self):
        self.step_move('Z', 'stepRight', 'negative')
       
    def turnLeft(self):  
        self.step_move('W', 'turnLeft',  'positive')
    
    def turnRight(self): 
        self.step_move('W', 'turnRight', 'negative')
    
    def stop(self):
        
        self._is_turning = False
        self._turn_dir = 0
        self._stride_dir_x = 0
        self._stride_dir_z = 0
        self.stop_requested = True

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
        
        self._is_turning = False
        self._turn_dir = 0
        self._stride_dir_x = 0
        self._stride_dir_z = 0
        self.stop_requested = True

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
        self.balance_flag = True
        self.order = ['', '', '', '', '']

        pos = self.postureBalance(0, 0, 0)
        self.changeCoordinates('Attitude Angle', pos=pos)

        time.sleep(2)
        self.imu.Error_value_accel_data, self.imu.Error_value_gyro_data = self.imu.average_filter()
        time.sleep(1)

        while True:
            if self.stop_requested:
                self.balance_flag = False
                break

            # IMU -> PID -> posture
            p, r, y = self.imu.update_imu()
            r = self.pid.PID_compute(r)
            p = self.pid.PID_compute(p)
            pos = self.postureBalance(r, p, 0)
            self.changeCoordinates('Attitude Angle', pos=pos)

            # Exit condition mirrors the old logic (no background thread)
            if ((self.order[0] == cmd.CMD_BALANCE and self.order[1] == '0')
                or (self.balance_flag and self.order[0] != '')):
                self.balance_flag = False
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
