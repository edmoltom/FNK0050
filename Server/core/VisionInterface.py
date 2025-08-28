from picamera2 import Picamera2
from core.vision.api import process_frame
from core.vision.viz_logger import VisionLogger
from core.vision.config_defaults import CAMERA_RESOLUTION, REF_SIZE

import cv2
import base64
import threading
import time
import os


class VisionInterface:
    """
    @brief VisionInterface wrapper using Picamera2 with a periodic vision pipeline.
    @details
    Captures frames at resolution defined in ``CAMERA_RESOLUTION``, runs a detection pipeline, draws overlays,
    and exposes the last processed frame as a base64-encoded JPEG string.
    The camera is started once on start_periodic_capture() and stopped on stop.
    """

    def __init__(self):
        """
        @brief Initialize the vision interface and default state.
        """
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_still_configuration(
                main={"size": CAMERA_RESOLUTION}
            )
        )
        self._config = {}              # Optional processing config (set via set_processing_config)
        self._last_encoded_image = None
        self._streaming = False
        self._thread = None
        self._lock = threading.Lock()
        self._camera_started = False
        
        self._logger = None
        if os.getenv("VISION_LOG", "0") == "1":
            stride = int(os.getenv("VISION_LOG_STRIDE", "5"))
            self._logger = VisionLogger(stride=stride, api_config={"stable": True})

    def set_processing_config(self, config: dict):
        """
        @brief Set runtime configuration for the processing pipeline.
        @param config Arbitrary dict consumed by the downstream pipeline.
        """
        self._config = dict(config or {})

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
        @note The camera must be started beforehand.
        """
        self._ensure_camera_started()
        return self.picam2.capture_array()

    # -------- Internal helpers --------

    def _get_reference_resolution(self, res: dict, frame_shape):
        """
        Try to infer the coordinate space used by the pipeline results.
        Fallbacks: config['ref_size'] or REF_SIZE.
        """
        # Try common keys
        if isinstance(res.get("space"), (tuple, list)) and len(res["space"]) == 2:
            ref_w, ref_h = res["space"]
        elif isinstance(res.get("space"), dict) and "width" in res["space"] and "height" in res["space"]:
            ref_w, ref_h = res["space"]["width"], res["space"]["height"]
        elif isinstance(res.get("input_size"), (tuple, list)) and len(res["input_size"]) == 2:
            ref_w, ref_h = res["input_size"]
        else:
            ref_w, ref_h = self._config.get("ref_size", REF_SIZE)

        # Guard rails
        if not (isinstance(ref_w, (int, float)) and isinstance(ref_h, (int, float)) and ref_w > 0 and ref_h > 0):
            ref_w, ref_h = REF_SIZE

        return float(ref_w), float(ref_h)

    def _apply_pipeline(self):
        """
        @brief Run the vision pipeline and draw overlays on the frame.
        @return BGR image with overlays.
        """
        frame_rgb = self.capture_array()                       # Picam2 → RGB
        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)     # OpenCV uses BGR

        # Try passing config; fall back if pipeline doesn't accept it
        try:
            res = process_frame(frame, return_overlay=False, config=self._config)
        except TypeError:
            res = process_frame(frame, return_overlay=False)

        if self._logger:
            self._logger.log_only(frame, out=res)

        if res and res.get("ok"):
            # Compute scaling from the pipeline's coordinate space to current frame
            ref_w, ref_h = self._get_reference_resolution(res, frame.shape)
            sx = frame.shape[1] / ref_w
            sy = frame.shape[0] / ref_h

            # Draw bbox if present
            if "bbox" in res and isinstance(res["bbox"], (tuple, list)) and len(res["bbox"]) == 4:
                x, y, w, h = res["bbox"]
                x2, y2, w2, h2 = int(x * sx), int(y * sy), int(w * sx), int(h * sy)
                cv2.rectangle(frame, (x2, y2), (x2 + w2, y2 + h2), (0, 255, 0), 2)

            # Draw center if present
            if "center" in res and isinstance(res["center"], (tuple, list)) and len(res["center"]) == 2:
                cx, cy = res["center"]
                cv2.circle(frame, (int(cx * sx), int(cy * sy)), 4, (0, 255, 0), -1)

            # Score label
            if "score" in res:
                label_y = max(18, (y2 if 'y2' in locals() else 10) - 6)
                cv2.putText(frame, f"sc={res['score']:.2f}", (10, label_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

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