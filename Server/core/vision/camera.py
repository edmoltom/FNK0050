"""Camera utilities for vision subsystem."""

import logging
import time
from typing import Tuple

import numpy as np

try:
    from picamera2 import Picamera2
except ImportError:  # pragma: no cover - handled gracefully when unavailable
    Picamera2 = None

from .config_defaults import CAMERA_RESOLUTION

logger = logging.getLogger(__name__)


class CameraCaptureError(RuntimeError):
    """Raised when the camera cannot provide frames."""


class Camera:
    """Simple camera wrapper providing RGB frames."""

    def __init__(
        self,
        resolution: Tuple[int, int] = CAMERA_RESOLUTION,
        max_failures: int = 3,
    ):
        self.resolution = resolution
        self._picam2 = None
        self._max_failures = max(1, int(max_failures))
        self._consec_failures = 0

    def start(self) -> None:
        """Open the camera device.

        Logs an error if the device cannot be opened. The camera remains
        ``None`` when unavailable so callers can detect the condition.
        """
        if self._picam2 is None:
            if Picamera2 is None:
                logger.error("Picamera2 library not available")
                return
            try:
                self._picam2 = Picamera2()
                config = self._picam2.create_video_configuration(
                    main={"size": self.resolution, "format": "RGB888"}
                )
                self._picam2.configure(config)
                self._picam2.start()
                time.sleep(0.5)

                self._picam2.set_controls({
                    "AeEnable": False,
                    "AwbEnable": False,        # si prefieres, déjalo True
                    "ExposureTime": 5000,      # 5 ms → mucho menos blur
                    "AnalogueGain": 4.0        # súbelo si queda oscuro (6–8)
                })
            except Exception:
                logger.error("Failed to open camera device", exc_info=True)
                self._picam2 = None

    def stop(self) -> None:
        """Release the camera device."""
        if self._picam2 is not None:
            try:
                self._picam2.stop()
                self._picam2.close()
            except Exception:
                logger.exception("Error while releasing camera device")
            finally:
                self._picam2 = None

    def is_running(self) -> bool:
        """Return ``True`` if the camera has been started."""
        return self._picam2 is not None

    def capture_rgb(self) -> np.ndarray:
        """Capture a single frame in RGB format.

        When the camera is unavailable or a frame cannot be read, a blank
        frame of the configured resolution is returned and a warning is logged.
        This allows callers to distinguish between legitimate black frames and
        camera errors by inspecting the logs.
        """
        if self._picam2 is None:
            self.start()
        if self._picam2 is None:
            self._consec_failures += 1
            logger.warning("Camera unavailable; returning blank frame")
            if self._consec_failures >= self._max_failures:
                raise CameraCaptureError("Camera unavailable")
            w, h = self.resolution
            return np.zeros((h, w, 3), dtype=np.uint8)
        try:
            frame = self._picam2.capture_array()
            self._consec_failures = 0
        except Exception as exc:
            self._consec_failures += 1
            logger.warning("Failed to read frame; returning blank frame", exc_info=True)
            if self._consec_failures >= self._max_failures:
                raise CameraCaptureError("Failed to read frame") from exc
            w, h = self.resolution
            return np.zeros((h, w, 3), dtype=np.uint8)

        return frame
