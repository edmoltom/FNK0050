import base64
import threading
import time
from typing import Optional, TYPE_CHECKING

import cv2

from .vision import api
from .vision.camera import Camera, CameraCaptureError
from .vision.overlays import draw_result

if TYPE_CHECKING:
    from .vision.viz_logger import VisionLogger


class VisionInterface:
    """Vision interface backed by :class:`Camera` and vision ``api``."""

    def __init__(
        self,
        max_capture_failures: int = 3,
        camera: Optional[Camera] = None,
        logger: Optional['VisionLogger'] = None,
    ) -> None:
        self.camera = camera or Camera(max_failures=max_capture_failures)
        self._config: dict = {}
        self._last_encoded_image: Optional[str] = None
        self._streaming = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._mode: Optional[str] = None
        self._last_error: Optional[Exception] = None

        self._logger: Optional['VisionLogger'] = logger or api.create_logger_from_env()

    # -------- Configuration API --------

    def set_processing_config(self, cfg: dict) -> None:
        """Store runtime configuration for the processing pipeline."""
        self._config = dict(cfg or {})

    def set_mode(self, mode: str) -> None:
        """Select detection mode: ``"object"`` or ``"face"``."""
        if mode not in {"object", "face"}:
            raise ValueError("mode must be 'object' or 'face'")
        self._mode = mode
        api.select_detector(mode)

    # -------- Camera control --------

    def start(self) -> None:
        """Start the underlying camera.

        Typically this is not required because :meth:`Camera.capture_rgb`
        automatically starts the device on first use.  This method is
        provided to allow callers to open the camera ahead of time or to
        surface initialization errors explicitly.
        """
        self.camera.start()

    def stop(self) -> None:
        """Stop streaming (if active) and release the camera."""
        self._streaming = False
        if self._thread:
            self._thread.join()
            self._thread = None
        self.camera.stop()
        if self._logger:
            self._logger.close()

    # -------- Internal helpers --------

    def _apply_pipeline(self):
        frame_rgb = self.camera.capture_rgb()
        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        api.process_frame(frame, return_overlay=True, config=self._config)
        if self._logger:
            self._logger.log(frame, result=api.get_last_result())
        frame = draw_result(frame, api.get_last_result())
        return frame

    # -------- Public API --------

    def start_stream(self, interval_sec: float = 1.0) -> None:
        """Start periodic capture and processing in a background thread.

        The camera will be started automatically on the first call to
        :meth:`Camera.capture_rgb`, so invoking :meth:`start` beforehand is
        optional.  The method performs a guard start to ensure the device is
        ready.
        """
        if self._streaming:
            print("[VisionInterface] Streaming already running.")
            return
        if not self.camera.is_running():
            self.camera.start()
        self._streaming = True

        def _capture_loop():
            period = max(0.0, float(interval_sec))
            next_tick = time.monotonic()
            while self._streaming:
                start = next_tick
                next_tick = start + period
                try:
                    frame = self._apply_pipeline()
                    ok, buffer = cv2.imencode(".jpg", frame)
                    if ok:
                        encoded = base64.b64encode(buffer).decode("utf-8")
                        with self._lock:
                            self._last_encoded_image = encoded
                except CameraCaptureError as e:
                    print(f"[VisionInterface] Capture error: {e}")
                    self._last_error = e
                    self._streaming = False
                    break
                except Exception as e:
                    print(f"[VisionInterface] Error in periodic capture: {e}")
                sleep_s = next_tick - time.monotonic()
                if sleep_s > 0:
                    time.sleep(sleep_s)
                else:
                    next_tick = time.monotonic()

        self._thread = threading.Thread(target=_capture_loop, daemon=True)
        self._thread.start()
        print("[VisionInterface] Started stream thread.")

    def snapshot(self) -> Optional[str]:
        """Capture, process and return a single frame as base64 JPEG."""
        frame = self._apply_pipeline()
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            return None
        encoded = base64.b64encode(buffer).decode("utf-8")
        with self._lock:
            self._last_encoded_image = encoded
        return encoded

    def get_last_processed_encoded(self) -> Optional[str]:
        """Return the last processed frame as base64-encoded JPEG."""
        with self._lock:
            return self._last_encoded_image

    def get_last_error(self) -> Optional[Exception]:
        """Return the last streaming error, if any."""
        return self._last_error
