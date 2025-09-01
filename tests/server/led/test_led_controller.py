import asyncio
import sys
import types

class _SpiDev:
    def __init__(self):
        self.mode = 0

    def open(self, bus, device):
        pass

    def close(self):
        pass

class _NPArray(list):
    def ravel(self):
        return self

spidev_stub = types.SimpleNamespace(SpiDev=_SpiDev)
numpy_stub = types.SimpleNamespace(
    array=lambda x: _NPArray(x),
    zeros=lambda n, dtype=None: [0] * n,
    uint8=int,
)
sys.modules.setdefault("spidev", spidev_stub)
sys.modules.setdefault("numpy", numpy_stub)

from Server.core.LedController import LedController

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
