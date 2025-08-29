"""Camera utilities for vision subsystem."""

import logging
from typing import Tuple

import cv2
import numpy as np

from .config_defaults import CAMERA_RESOLUTION

logger = logging.getLogger(__name__)


class Camera:
    """Simple camera wrapper providing RGB frames."""

    def __init__(self, resolution: Tuple[int, int] = CAMERA_RESOLUTION):
        self.resolution = resolution
        self._cap = None

    def start(self) -> None:
        """Open the camera device.

        Logs an error if the device cannot be opened. The camera remains
        ``None`` when unavailable so callers can detect the condition.
        """
        if self._cap is None:
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                logger.error("Failed to open camera device 0")
                self._cap.release()
                self._cap = None
                return
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

    def stop(self) -> None:
        """Release the camera device."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def capture_rgb(self) -> np.ndarray:
        """Capture a single frame in RGB format.

        When the camera is unavailable or a frame cannot be read, a blank
        frame of the configured resolution is returned and a warning is logged.
        This allows callers to distinguish between legitimate black frames and
        camera errors by inspecting the logs.
        """
        if self._cap is None:
            self.start()
        if self._cap is None or not self._cap.isOpened():
            logger.warning("Camera unavailable; returning blank frame")
            w, h = self.resolution
            return np.zeros((h, w, 3), dtype=np.uint8)
        ret, frame = self._cap.read()
        if not ret:
            logger.warning("Failed to read frame; returning blank frame")
            w, h = self.resolution
            return np.zeros((h, w, 3), dtype=np.uint8)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
