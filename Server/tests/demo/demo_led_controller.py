from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SERVER_ROOT = PROJECT_ROOT / "Server"

for path in (PROJECT_ROOT, SERVER_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from Server.interface.LedController import LedController

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
