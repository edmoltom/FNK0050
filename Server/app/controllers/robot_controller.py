from __future__ import annotations

import asyncio
import time
from typing import Any, Dict

from ..services.movement_service import MovementService
from ..services.vision_service import VisionService
from core.vision import api as vision_api


class RobotController:
    """Handle high level robot commands and delegate to services."""

    def __init__(self, movement: MovementService, vision: VisionService) -> None:
        self._movement = movement
        self._vision = vision

    async def _wait_for_frame(self, timeout: float = 3.0, poll: float = 0.05):
        """Wait until a processed frame is available or timeout."""
        deadline = time.monotonic() + float(timeout)
        img_str = self._vision.get_last_processed_encoded()
        while img_str is None and time.monotonic() < deadline:
            await asyncio.sleep(poll)
            img_str = self._vision.get_last_processed_encoded()
        return img_str

    async def handle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch an incoming command dictionary."""
        cmd = data.get("cmd")
        if cmd == "ping":
            return {"status": "ok", "type": "text", "data": "pong"}

        if cmd == "start":
            interval = float(data.get("interval", 1.0))
            self._vision.start(interval_sec=interval)
            return {"status": "ok", "type": "text", "data": f"capture started @ {interval}s"}

        if cmd == "stop":
            self._vision.stop()
            return {"status": "ok", "type": "text", "data": "capture stopped"}

        if cmd == "stream_start":
            # start the vision streaming generator
            self._vision.stream()
            return {"status": "ok", "type": "text", "data": "streaming started"}

        if cmd == "stream_stop":
            self._vision.stop()
            return {"status": "ok", "type": "text", "data": "streaming stopped"}

        if cmd == "capture":
            img_str = await self._wait_for_frame(timeout=float(data.get("timeout", 2.0)))
            if img_str is None:
                return {"status": "wait", "type": "text", "data": "no frame yet"}
            return {"status": "ok", "type": "image", "data": img_str}

        if cmd == "process":
            allowed = {"blur", "edges", "contours", "ref_size"}
            config = {k: v for k, v in data.items() if k in allowed}
            self._vision.set_processing_config(config)
            return {"status": "ok", "type": "text", "data": "processing config updated"}

        if cmd == "load_profile":
            which = data.get("which", "big")
            path = data.get("path")
            vision_api.load_profile(which, path)
            return {"status": "ok", "type": "text", "data": f"profile {which} loaded"}

        if cmd == "dynamic":
            which = data.get("which", "big")
            params = data.get("params", {})
            vision_api.update_dynamic(which, params)
            return {"status": "ok", "type": "text", "data": "dynamic params updated"}

        if cmd == "walk":
            vx = float(data.get("vx", 0.0))
            vy = float(data.get("vy", 0.0))
            omega = float(data.get("omega", 0.0))
            self._movement.walk(vx, vy, omega)
            return {"status": "ok", "type": "text", "data": "walk command dispatched"}

        if cmd == "movement_stop":
            self._movement.stop()
            return {"status": "ok", "type": "text", "data": "movement stopped"}

        return {"status": "error", "type": "text", "data": f"unknown command: {cmd}"}
