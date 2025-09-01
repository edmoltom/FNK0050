# test_codes/test_led.py
import time
from led.led import Led   # core/led/__init__.py must exist

def main():
    print("LED test: SPI (PCB v2)")
    led = Led(count=8, brightness=30)  # ajusta count a tus LEDs
    try:
        led.colorWipe([255, 0, 0], 50)
        led.colorWipe([0, 255, 0], 50)
        led.colorWipe([0, 0, 255], 50)
        time.sleep(0.5)
        led.set_all([255, 255, 255]); led.show(); time.sleep(0.5)
    finally:
        led.off()
        led.close()
        print("LED test done.")
