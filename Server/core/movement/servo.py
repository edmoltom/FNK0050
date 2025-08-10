from .PCA9685 import PCA9685

class Servo:
    """
    @brief High-level servo helper using a PCA9685 driver.
    """

    def __init__(self,
                 address=0x40,
                 debug=False,
                 angle_min=18,
                 angle_max=162,
                 ticks_min=102,
                 ticks_max=512,
                 freq_hz=50):
        self.angleMin = angle_min
        self.angleMax = angle_max
        self.ticks_min = ticks_min
        self.ticks_max = ticks_max

        self.pwm = PCA9685(address=address, debug=debug)
        if hasattr(self.pwm, "set_pwm_freq"):
            self.pwm.set_pwm_freq(freq_hz)
        else:
            self.pwm.setPWMFreq(freq_hz)  # legacy

    @staticmethod
    def _map(value, from_low, from_high, to_low, to_high):
        return (to_high - to_low) * (value - from_low) / (from_high - from_low) + to_low

    def set_servo_angle(self, channel, angle):
        if angle < self.angleMin: angle = self.angleMin
        elif angle > self.angleMax: angle = self.angleMax

        ticks = self._map(angle, 0, 180, self.ticks_min, self.ticks_max)
        if hasattr(self.pwm, "set_pwm"):
            self.pwm.set_pwm(channel, 0, int(ticks))
        else:
            self.pwm.setPWM(channel, 0, int(ticks))  # legacy

    # Legacy alias
    def setServoAngle(self, channel, angle):
        self.set_servo_angle(channel, angle)


if __name__ == '__main__':
    S = Servo()
    try:
        while True:
            for i in range(16):
                S.set_servo_angle(i, 90)
    except KeyboardInterrupt:
        pass