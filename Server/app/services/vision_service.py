from __future__ import annotations
from typing import Optional, Callable, Dict, Any

import cv2

from core.VisionManager import VisionManager
import core.vision.profile_manager as pm
from core.vision import api
from core.vision.pipeline.face_pipeline import FacePipeline

class VisionService:
    def __init__(
        self,
        vm: Optional[VisionManager] = None,
        mode: str = "object",
        camera_fps: float = 15.0,
        face_cfg: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.vm = vm or VisionManager()
        self._mode = mode
        self._running = False
        self._camera_fps = float(camera_fps)
        self._face_cfg = dict(face_cfg or {})

    def start(
        self,
        interval_sec: float = 1.0,
        frame_handler: Optional[Callable[[dict | None], None]] = None,
    ) -> None:
        if not self._running:
            try:
                cv2.setNumThreads(1)
            except Exception:
                pass
            if self._face_cfg:
                api.register_pipeline("face", FacePipeline(self._face_cfg))
            pm._profiles.setdefault("vision", {}).update({"camera_fps": self._camera_fps})
            self.vm.select_pipeline(self._mode)
            self.vm.start()
            self.vm.start_stream(interval_sec=interval_sec, on_frame=frame_handler)
            self._running = True

    def stop(self) -> None:
        if self._running:
            self.vm.stop()
            self._running = False

    def last_b64(self) -> Optional[str]:
        return self.vm.get_last_processed_encoded()

    def snapshot_b64(self) -> Optional[str]:
        return self.vm.snapshot()

