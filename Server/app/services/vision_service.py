from __future__ import annotations
from typing import Optional, Callable, Dict, Any

import cv2

from interface.VisionManager import VisionManager
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
        self._frame_callback: Optional[Callable[[dict | None], None]] = None
        self._registered_face_profile: Optional[str] = None

    def register_face_pipeline(self, profile_name: str) -> None:
        if not self._face_cfg:
            return

        if self._registered_face_profile == profile_name:
            self.vm.select_pipeline(profile_name)
            return

        pipeline = FacePipeline(self._face_cfg)
        api.register_pipeline(profile_name, pipeline)
        pm._profiles.setdefault("vision", {}).update({"camera_fps": self._camera_fps})
        self.vm.select_pipeline(profile_name)
        self._registered_face_profile = profile_name

    def set_frame_callback(
        self, cb: Optional[Callable[[dict | None], None]]
    ) -> None:
        self._frame_callback = cb

    def start(
        self,
        interval_sec: float = 1.0,
        frame_handler: Optional[Callable[[dict | None], None]] = None,
    ) -> None:
        handler = frame_handler if frame_handler is not None else self._frame_callback
        if not self._running:
            try:
                cv2.setNumThreads(1)
            except Exception:
                pass
            if not self._face_cfg:
                pm._profiles.setdefault("vision", {}).update(
                    {"camera_fps": self._camera_fps}
                )
                self.vm.select_pipeline(self._mode)
            self.vm.start()
            self.vm.start_stream(interval_sec=interval_sec, on_frame=handler)
            self._running = True

    def stop(self) -> None:
        if self._running:
            self.vm.stop()
            self._running = False

    def last_b64(self) -> Optional[str]:
        return self.vm.get_last_processed_encoded()

    def snapshot_b64(self) -> Optional[str]:
        return self.vm.snapshot()

