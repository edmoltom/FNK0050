import math
from .kalman import KalmanFilter
from mpu6050 import mpu6050


class IMU:
    """
    @brief Inertial Measurement Unit handler with sensor fusion using Kalman filtering.
    @details
    Reads data from an MPU6050 accelerometer/gyroscope and estimates pitch, roll, and yaw
    using quaternion-based sensor fusion with proportional–integral correction.
    """

    def __init__(self,
                 process_noise=0.001,
                 measurement_noise=0.1,
                 kp=100.0,
                 ki=0.002,
                 half_sampling_period=0.001,
                 address=0x68):
        self.Kp = kp
        self.Ki = ki
        self.halfT = half_sampling_period

        self.q0, self.q1, self.q2, self.q3 = 1.0, 0.0, 0.0, 0.0
        self.exInt = self.eyInt = self.ezInt = 0.0

        self.pitch = self.roll = self.yaw = 0.0
        self.accel_x = self.accel_y = self.accel_z = 0.0

        self.sensor = mpu6050(address=address)
        self.sensor.set_accel_range(mpu6050.ACCEL_RANGE_2G)
        self.sensor.set_gyro_range(mpu6050.GYRO_RANGE_250DEG)

        self.kalman_filter_AX = KalmanFilter(process_noise, measurement_noise)
        self.kalman_filter_AY = KalmanFilter(process_noise, measurement_noise)
        self.kalman_filter_AZ = KalmanFilter(process_noise, measurement_noise)
        self.kalman_filter_GX = KalmanFilter(process_noise, measurement_noise)
        self.kalman_filter_GY = KalmanFilter(process_noise, measurement_noise)
        self.kalman_filter_GZ = KalmanFilter(process_noise, measurement_noise)

        self.Error_value_accel_data, self.Error_value_gyro_data = self.average_filter()

    def average_filter(self):
        sum_accel_x = sum_accel_y = sum_accel_z = 0.0
        sum_gyro_x = sum_gyro_y = sum_gyro_z = 0.0

        for _ in range(100):
            accel_data = self.sensor.get_accel_data()
            gyro_data = self.sensor.get_gyro_data()
            sum_accel_x += accel_data['x']; sum_accel_y += accel_data['y']; sum_accel_z += accel_data['z']
            sum_gyro_x  += gyro_data['x'];  sum_gyro_y  += gyro_data['y'];  sum_gyro_z  += gyro_data['z']

        sum_accel_x /= 100; sum_accel_y /= 100; sum_accel_z /= 100
        sum_gyro_x  /= 100; sum_gyro_y  /= 100; sum_gyro_z  /= 100

        accel_data['x'] = sum_accel_x
        accel_data['y'] = sum_accel_y
        accel_data['z'] = sum_accel_z - 9.8

        gyro_data['x'] = sum_gyro_x
        gyro_data['y'] = sum_gyro_y
        gyro_data['z'] = sum_gyro_z

        return accel_data, gyro_data

    def update_imu(self):
        accel_data = self.sensor.get_accel_data()
        gyro_data = self.sensor.get_gyro_data()

        ax = self.kalman_filter_AX.update_kalman(accel_data['x'] - self.Error_value_accel_data['x'])
        ay = self.kalman_filter_AY.update_kalman(accel_data['y'] - self.Error_value_accel_data['y'])
        az = self.kalman_filter_AZ.update_kalman(accel_data['z'] - self.Error_value_accel_data['z'])
        gx = self.kalman_filter_GX.update_kalman(gyro_data['x'] - self.Error_value_gyro_data['x'])
        gy = self.kalman_filter_GY.update_kalman(gyro_data['y'] - self.Error_value_gyro_data['y'])
        gz = self.kalman_filter_GZ.update_kalman(gyro_data['z'] - self.Error_value_gyro_data['z'])

        norm = math.sqrt(ax*ax + ay*ay + az*az)
        ax /= norm; ay /= norm; az /= norm

        vx = 2 * (self.q1*self.q3 - self.q0*self.q2)
        vy = 2 * (self.q0*self.q1 + self.q2*self.q3)
        vz = self.q0*self.q0 - self.q1*self.q1 - self.q2*self.q2 + self.q3*self.q3

        ex = (ay * vz - az * vy)
        ey = (az * vx - ax * vz)
        ez = (ax * vy - ay * vx)

        self.exInt += ex * self.Ki; self.eyInt += ey * self.Ki; self.ezInt += ez * self.Ki

        gx += self.Kp * ex + self.exInt
        gy += self.Kp * ey + self.eyInt
        gz += self.Kp * ez + self.ezInt

        self.q0 += (-self.q1*gx - self.q2*gy - self.q3*gz) * self.halfT
        self.q1 += ( self.q0*gx + self.q2*gz - self.q3*gy) * self.halfT
        self.q2 += ( self.q0*gy - self.q1*gz + self.q3*gx) * self.halfT
        self.q3 += ( self.q0*gz + self.q1*gy - self.q2*gx) * self.halfT

        norm = math.sqrt(self.q0*self.q0 + self.q1*self.q1 + self.q2*self.q2 + self.q3*self.q3)
        self.q0/=norm; self.q1/=norm; self.q2/=norm; self.q3/=norm

        self.pitch = math.asin(-2*self.q1*self.q3 + 2*self.q0*self.q2) * 57.3
        self.roll  = math.atan2(2*self.q2*self.q3 + 2*self.q0*self.q1,
                                -2*self.q1*self.q1 - 2*self.q2*self.q2 + 1) * 57.3
        self.yaw   = math.atan2(2*(self.q1*self.q2 + self.q0*self.q3),
                                self.q0*self.q0 + self.q1*self.q1 - self.q2*self.q2 - self.q3*self.q3) * 57.3

        self.accel_x, self.accel_y, self.accel_z = ax, ay, az
        return self.pitch, self.roll, self.yaw, self.accel_x, self.accel_y, self.accel_z

    # Backward-compat alias
    def imuUpdate(self):
        return self.update_imu()
