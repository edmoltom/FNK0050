import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from LedController import LedController

async def test_led_no_block():
    ctrl = LedController(brightness=30)
    try:
        await ctrl.set_all([255, 0, 0])
        await asyncio.sleep(0.2)
        await ctrl.color_wipe([0, 255, 0], 50)
        await asyncio.sleep(0.2)
        await ctrl.rainbow(wait_ms=5)
        await asyncio.sleep(1)
    finally:
        await ctrl.close()


def main():
    asyncio.run(test_led_no_block())