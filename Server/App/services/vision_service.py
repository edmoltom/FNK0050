from __future__ import annotations
from typing import Optional, Dict, Any

from ...core.VisionInterface import VisionInterface

class VisionService:
    def __init__(self, vi: Optional[VisionInterface] = None) -> None:
        self.vi = vi or VisionInterface()
        self._running = False

    def start(self, interval_sec: float = 1.0) -> None:
        if not self._running:
            self.vi.start()
            self.vi.start_stream(interval_sec=interval_sec)
            self._running = True

    def stop(self) -> None:
        if self._running:
            self.vi.stop()
            self._running = False

    def last_b64(self) -> Optional[str]:
        return self.vi.get_last_processed_encoded()

    def snapshot_b64(self) -> Optional[str]:
        return self.vi.snapshot()

    def set_processing(self, cfg: Dict[str, Any]) -> None:
        allowed = {"blur", "edges", "contours", "ref_size"}
        filtered = {k: v for k, v in (cfg or {}).items() if k in allowed}
        if filtered:
            self.vi.set_processing_config(filtered)
