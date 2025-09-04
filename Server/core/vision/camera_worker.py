import threading
import time
from typing import Optional, Tuple

import numpy as np

from .camera import Camera


class CameraWorker(threading.Thread):
    """Background worker capturing frames from a camera."""

    def __init__(self, camera: Camera, max_fps: float = 15.0) -> None:
        super().__init__(daemon=True)
        self.camera = camera
        self.max_fps = max_fps
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_ts: Optional[float] = None
        self._lock = threading.Lock()
        self._stop = False

    def run(self) -> None:  # pragma: no cover - threading timing
        interval = 1.0 / self.max_fps if self.max_fps > 0 else 0.0
        while not self._stop:
            start = time.time()
            frame = self.camera.capture_rgb()
            with self._lock:
                self.latest_frame = frame
                self.latest_ts = start
            elapsed = time.time() - start
            sleep = interval - elapsed
            if sleep > 0:
                time.sleep(sleep)

    def get_latest(self) -> Optional[Tuple[np.ndarray, float]]:
        with self._lock:
            if self.latest_frame is None or self.latest_ts is None:
                return None
            return self.latest_frame.copy(), self.latest_ts

    def stop(self) -> None:
        self._stop = True
        self.join()
        self.camera.stop()
