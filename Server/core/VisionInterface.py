from picamera2 import Picamera2
from core.vision.engine import VisionEngine
from core.vision.logger import VizLogger
from core.vision.config_defaults import CAMERA_RESOLUTION
from core.vision.overlays import draw_engine

import cv2
import base64
import threading
import time
import os


class VisionInterface:
    """
    @brief Vision interface wrapper using Picamera2 with a periodic vision pipeline.
    @details
    Captures frames at resolution defined in ``CAMERA_RESOLUTION``, runs a detection pipeline, draws overlays,
    and exposes the last processed frame as a base64-encoded JPEG string.
    The camera is started once on start_periodic_capture() and stopped on stop.
    """

    def __init__(self):
        """
        @brief Initialize the camera and default state.
        """
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_still_configuration(
                main={"size": CAMERA_RESOLUTION}
            )
        )
        self._engine = VisionEngine()
        self._config = {}              # Optional processing config (set via set_processing_config)
        self._last_encoded_image = None
        self._streaming = False
        self._thread = None
        self._lock = threading.Lock()
        self._camera_started = False
        
        self._logger = None
        if os.getenv("VISION_LOG", "0") == "1":
            stride = int(os.getenv("VISION_LOG_STRIDE", "5"))
            save_raw = os.getenv("VISION_LOG_RAW", "0") == "1"
            self._logger = VizLogger(stride=stride, save_raw=save_raw)
            self._engine.set_logger(self._logger)

    def set_processing_config(self, config: dict):
        """
        @brief Set runtime configuration for the processing pipeline.
        @param config Arbitrary dict consumed by the downstream pipeline.
        """
        self._config = dict(config or {})
        self._engine.config = self._config
        self._engine.reload_config()

    def _ensure_camera_started(self):
        if not self._camera_started:
            self.picam2.start()
            self._camera_started = True

    def _ensure_camera_stopped(self):
        if self._camera_started:
            self.picam2.stop()
            self._camera_started = False

    def capture_array(self):
        """
        @brief Capture a single RGB frame as a NumPy array.
        @return RGB image (H, W, 3).
        @note Camera must be started beforehand.
        """
        self._ensure_camera_started()
        return self.picam2.capture_array()

    def _apply_pipeline(self):
        """
        @brief Run the vision pipeline and draw overlays on the frame.
        @return BGR image with overlays.
        """
        frame_rgb = self.capture_array()                       # Picam2 → RGB
        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)     # OpenCV uses BGR

        # Try passing config; fall back if pipeline doesn't accept it
        res = self._engine.process(frame)
        frame = draw_engine(frame, res)
        return frame

    # -------- Public streaming API --------

    def start_periodic_capture(self, interval=1.0):
        """
        @brief Start a background thread that captures and processes frames periodically.
        @param interval Desired seconds between captures (processing time compensated).
        @note Stores the last processed frame as base64 JPEG in _last_encoded_image.
        """
        if self._streaming:
            print("[VisionInterface] Streaming already running.")
            return
        self._streaming = True
        self._ensure_camera_started()

        def _capture_loop():
            period = max(0.0, float(interval))
            next_tick = time.monotonic()
            while self._streaming:
                start = next_tick
                next_tick = start + period

                try:
                    frame = self._apply_pipeline()
                    ok, buffer = cv2.imencode('.jpg', frame)
                    if ok:
                        encoded = base64.b64encode(buffer).decode("utf-8")
                        with self._lock:
                            self._last_encoded_image = encoded
                except Exception as e:
                    print(f"[VisionInterface] Error in periodic capture: {e}")

                # Compensate processing time to keep cadence
                sleep_s = next_tick - time.monotonic()
                if sleep_s > 0:
                    time.sleep(sleep_s)
                else:
                    # We're lagging; skip sleep to catch up next loop
                    next_tick = time.monotonic()

        self._thread = threading.Thread(target=_capture_loop, daemon=True)
        self._thread.start()
        print("[VisionInterface] Started periodic capture.")

    def stop_periodic_capture(self):
        """
        @brief Stop the background thread and wait for clean shutdown.
        """
        self._streaming = False
        if self._thread:
            self._thread.join()
            self._thread = None
        self._ensure_camera_stopped()
        if self._logger:
            self._logger.close()
        print("[VisionInterface] Stopped periodic capture.")

    def get_last_processed_encoded(self):
        """
        @brief Get the last processed frame as a base64-encoded JPEG.
        @return str or None.
        """
        with self._lock:
            return self._last_encoded_image
