from __future__ import annotations
from typing import Optional, Callable

from core.VisionManager import VisionManager

class VisionService:
    def __init__(self, vm: Optional[VisionManager] = None, mode: str = "object") -> None:
        self.vm = vm or VisionManager()
        self._mode = mode
        self._running = False

    def start(
        self,
        interval_sec: float = 1.0,
        frame_handler: Optional[Callable[[dict], None]] = None,
    ) -> None:
        if not self._running:
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

