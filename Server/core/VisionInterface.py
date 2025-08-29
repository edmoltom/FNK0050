import base64
import os
import threading
import time
from typing import Optional

import cv2

from core.vision import api
from core.vision.camera import Camera, CameraCaptureError
from core.vision.config_defaults import REF_SIZE
from core.vision.viz_logger import VisionLogger


class VisionInterface:
    """Vision interface backed by :class:`Camera` and vision ``api``."""

    def __init__(self, max_capture_failures: int = 3) -> None:
        self.camera = Camera(max_failures=max_capture_failures)
        self._config: dict = {}
        self._last_encoded_image: Optional[str] = None
        self._streaming = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._mode: Optional[str] = None
        self._last_error: Optional[Exception] = None

        self._logger = None
        if os.getenv("VISION_LOG", "0") == "1":
            stride = int(os.getenv("VISION_LOG_STRIDE", "5"))
            self._logger = VisionLogger(stride=stride, api_config={"stable": True})

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

    def _get_reference_resolution(self, res: dict, frame_shape):
        if isinstance(res.get("space"), (tuple, list)) and len(res["space"]) == 2:
            ref_w, ref_h = res["space"]
        elif (
            isinstance(res.get("space"), dict)
            and "width" in res["space"]
            and "height" in res["space"]
        ):
            ref_w, ref_h = res["space"]["width"], res["space"]["height"]
        elif isinstance(res.get("input_size"), (tuple, list)) and len(res["input_size"]) == 2:
            ref_w, ref_h = res["input_size"]
        else:
            ref_w, ref_h = self._config.get("ref_size", REF_SIZE)

        if not (
            isinstance(ref_w, (int, float))
            and isinstance(ref_h, (int, float))
            and ref_w > 0
            and ref_h > 0
        ):
            ref_w, ref_h = REF_SIZE
        return float(ref_w), float(ref_h)

    def _apply_pipeline(self):
        frame_rgb = self.camera.capture_rgb()
        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        try:
            res = api.process_frame(frame, return_overlay=False, config=self._config)
        except TypeError:
            res = api.process_frame(frame, return_overlay=False)
        if self._logger:
            self._logger.log_only(frame, out=res)
        if res and res.get("ok"):
            ref_w, ref_h = self._get_reference_resolution(res, frame.shape)
            sx = frame.shape[1] / ref_w
            sy = frame.shape[0] / ref_h
            if (
                "bbox" in res
                and isinstance(res["bbox"], (tuple, list))
                and len(res["bbox"]) == 4
            ):
                x, y, w, h = res["bbox"]
                x2, y2, w2, h2 = int(x * sx), int(y * sy), int(w * sx), int(h * sy)
                cv2.rectangle(frame, (x2, y2), (x2 + w2, y2 + h2), (0, 255, 0), 2)
            if (
                "center" in res
                and isinstance(res["center"], (tuple, list))
                and len(res["center"]) == 2
            ):
                cx, cy = res["center"]
                cv2.circle(frame, (int(cx * sx), int(cy * sy)), 4, (0, 255, 0), -1)
            if "score" in res:
                label_y = max(18, (locals().get("y2", 10)) - 6)
                cv2.putText(
                    frame,
                    f"sc={res['score']:.2f}",
                    (10, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
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
