# test_codes/test_led.py
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SERVER_ROOT = PROJECT_ROOT / "Server"

for path in (PROJECT_ROOT, SERVER_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from Server.core.led.led import Led

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
