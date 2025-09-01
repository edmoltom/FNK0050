import time
import math

try:
    import smbus  # type: ignore
except ImportError:
    smbus = None


class PCA9685:
    """
    @brief Driver for the PCA9685 16-channel PWM controller.
    @details
    Provides methods to configure PWM frequency and control individual channels
    via I2C. Includes basic error handling to avoid crashes when the I2C bus
    is unavailable.
    """

    # Register addresses
    __SUBADR1 = 0x02
    __SUBADR2 = 0x03
    __SUBADR3 = 0x04
    __MODE1 = 0x00
    __PRESCALE = 0xFE
    __LED0_ON_L = 0x06
    __LED0_ON_H = 0x07
    __LED0_OFF_L = 0x08
    __LED0_OFF_H = 0x09
    __ALLLED_ON_L = 0xFA
    __ALLLED_ON_H = 0xFB
    __ALLLED_OFF_L = 0xFC
    __ALLLED_OFF_H = 0xFD

    def __init__(self, address=0x40, i2c_bus=1, debug=False):
        """
        @brief Initializes the PCA9685 driver.
        @param address I2C address of the PCA9685.
        @param i2c_bus I2C bus number (1 for Raspberry Pi >= Rev 2).
        @param debug Enables debug prints when True.
        @throws ImportError if smbus is not available.
        @throws OSError if I2C bus/device cannot be opened.
        """
        if smbus is None:
            raise ImportError("smbus module not found. Install smbus/smbus2 on target device.")

        self.debug = debug
        try:
            self.bus = smbus.SMBus(i2c_bus)
        except OSError as e:
            raise OSError(f"Unable to open I2C bus {i2c_bus}: {e}") from e

        self.address = address
        self._safe_write(self.__MODE1, 0x00)  # Reset MODE1 register

    # ------------------------ Low-level I2C ------------------------

    def _safe_write(self, reg, value):
        """
        @brief Writes an 8-bit value to the specified register.
        @param reg Register address.
        @param value 8-bit value to write.
        """
        try:
            self.bus.write_byte_data(self.address, reg, value & 0xFF)
            if self.debug:
                print(f"[PCA9685] WRITE addr=0x{self.address:02X} reg=0x{reg:02X} val=0x{value & 0xFF:02X}")
        except OSError as e:
            if self.debug:
                print(f"[PCA9685] WRITE FAILED reg=0x{reg:02X}: {e}")
            raise

    def _safe_read(self, reg):
        """
        @brief Reads an unsigned byte from the specified register.
        @param reg Register address.
        @return Value read from the device.
        """
        try:
            val = self.bus.read_byte_data(self.address, reg)
            if self.debug:
                print(f"[PCA9685] READ addr=0x{self.address:02X} reg=0x{reg:02X} -> 0x{val:02X}")
            return val
        except OSError as e:
            if self.debug:
                print(f"[PCA9685] READ FAILED reg=0x{reg:02X}: {e}")
            raise

    # ------------------------ High-level API ------------------------

    def set_pwm_freq(self, freq):
        """
        @brief Sets the PWM frequency for all channels.
        @param freq Desired frequency in Hz.
        """
        if freq <= 0:
            raise ValueError("freq must be > 0")

        prescaleval = 25_000_000.0  # 25 MHz clock
        prescaleval /= 4096.0       # 12-bit resolution
        prescaleval /= float(freq)
        prescaleval -= 1.0
        prescale = math.floor(prescaleval + 0.5)

        oldmode = self._safe_read(self.__MODE1)
        newmode = (oldmode & 0x7F) | 0x10  # Sleep
        self._safe_write(self.__MODE1, newmode)
        self._safe_write(self.__PRESCALE, int(prescale))
        self._safe_write(self.__MODE1, oldmode)
        time.sleep(0.005)
        self._safe_write(self.__MODE1, oldmode | 0x80)  # Restart

    def set_pwm(self, channel, on, off):
        """
        @brief Sets the PWM on/off values for a specific channel.
        @param channel Channel number (0-15).
        @param on Value at which PWM turns on (0-4095).
        @param off Value at which PWM turns off (0-4095).
        """
        if not 0 <= channel <= 15:
            raise ValueError("channel must be in [0, 15]")
        on = max(0, min(4095, int(on)))
        off = max(0, min(4095, int(off)))

        base = self.__LED0_ON_L + 4 * channel
        self._safe_write(base + 0, on & 0xFF)
        self._safe_write(base + 1, on >> 8)
        self._safe_write(base + 2, off & 0xFF)
        self._safe_write(base + 3, off >> 8)

    def set_motor_pwm(self, channel, duty):
        """
        @brief Sets motor PWM duty cycle for a given channel.
        @param channel Channel number (0-15).
        @param duty Duty cycle value (0-4095).
        """
        self.set_pwm(channel, 0, duty)

    def set_servo_pulse(self, channel, pulse_us):
        """
        @brief Sets the servo pulse width for a specific channel.
        @details
        Assumes a PWM frequency of 50Hz (20ms period). Converts microseconds
        to the corresponding 12-bit PWM value.
        @param channel Channel number (0-15).
        @param pulse_us Pulse width in microseconds.
        """
        ticks = int((pulse_us * 4096) / 20000)  # 50Hz → 20,000us period
        self.set_pwm(channel, 0, ticks)


if __name__ == '__main__':
    pass
