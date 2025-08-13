import math

class Odometry:
    def __init__(self, stride_gain=0.55, zupt_gyro_thresh_dps=3.0):
        self.x = 0.0; self.y = 0.0; self.theta = 0.0  # rad
        self._last_sin = 0.0
        self.stride_gain = stride_gain
        self.zupt_gyro_thresh = zupt_gyro_thresh_dps

    def set_heading_deg(self, yaw_deg):
        self.theta = math.radians(yaw_deg)

    def tick_gait(self, phase_deg, step_length):
        s = math.sin(math.radians(phase_deg))
        if self._last_sin <= 0.0 and s > 0.0:           # “evento de zancada”
            ds = self.stride_gain * step_length         # mm por zancada
            self.x += ds * math.cos(self.theta)
            self.y += ds * math.sin(self.theta)
        self._last_sin = s

    def zupt(self, is_stance, gyro_z_dps):
        # Si estamos en apoyo y el giro es casi nulo, “ancla” el estado
        if is_stance and abs(gyro_z_dps) < self.zupt_gyro_thresh:
            # Aquí no integramos nada. Si usas velocidades, aquí las pondrías a 0.
            return True
        return False
