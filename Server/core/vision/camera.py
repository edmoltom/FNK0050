import cv2
import numpy as np
from typing import Tuple

from .config_defaults import CAMERA_RESOLUTION


class Camera:
    """Simple camera wrapper providing RGB frames."""

    def __init__(self, resolution: Tuple[int, int] = CAMERA_RESOLUTION):
        self.resolution = resolution
        self._cap = None

    def start(self) -> None:
        """Open the camera device."""
        if self._cap is None:
            self._cap = cv2.VideoCapture(0)
            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

    def stop(self) -> None:
        """Release the camera device."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def capture_rgb(self) -> np.ndarray:
        """Capture a single frame in RGB format."""
        if self._cap is None:
            self.start()
        if self._cap is None or not self._cap.isOpened():
            # Fallback to blank frame if no camera is available
            w, h = self.resolution
            return np.zeros((h, w, 3), dtype=np.uint8)
        ret, frame = self._cap.read()
        if not ret:
            w, h = self.resolution
            return np.zeros((h, w, 3), dtype=np.uint8)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
