from picamera2 import Picamera2
from core.vision.engine import VisionEngine
from core.vision.config_defaults import CAMERA_RESOLUTION
from core.vision.overlays import draw_engine

import cv2
import base64
import threading
import time


class VisionInterface:
    """Lightweight camera wrapper that captures frames and streams processed output.

    The interface is agnostic of detection details and delegates processing to a
    provided :class:`VisionEngine`. Its sole responsibilities are:

    * Capturing frames from ``Picamera2``.
    * Running the provided engine on each frame.
    * Encoding the result to base64 JPEG for streaming.
    """

    def __init__(self, engine: VisionEngine):
        """Initialise the camera and internal state.

        Parameters
        ----------
        engine: VisionEngine
            Instance used to process captured frames.
        """
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_still_configuration(
                main={"size": CAMERA_RESOLUTION}
            )
        )
        self._engine = engine
        self._last_encoded_image = None
        self._streaming = False
        self._thread = None
        self._lock = threading.Lock()
        self._camera_started = False

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
        res = self._engine.process(frame)
        frame = draw_engine(frame, res)
        return frame

    # -------- Public streaming API --------

    def start(self, interval: float = 1.0) -> None:
        """Start capturing and processing frames in a background thread.

        Parameters
        ----------
        interval: float, optional
            Desired seconds between captures. Processing time is compensated to
            maintain this cadence.
        """
        if self._streaming:
            print("[VisionInterface] Streaming already running.")
            return
        self._streaming = True
        self._ensure_camera_started()

        def _capture_loop() -> None:
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
                except Exception as e:  # pragma: no cover - capture loop should not raise
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
        print("[VisionInterface] Started capture thread.")

    def stop(self) -> None:
        """Stop the background capture thread and release the camera."""
        self._streaming = False
        if self._thread:
            self._thread.join()
            self._thread = None
        self._ensure_camera_stopped()
        print("[VisionInterface] Stopped capture thread.")

    # Backwards compatibility wrappers
    def start_periodic_capture(self, interval: float = 1.0) -> None:  # pragma: no cover
        self.start(interval)

    def stop_periodic_capture(self) -> None:  # pragma: no cover
        self.stop()

    def get_last_processed_encoded(self):
        """
        @brief Get the last processed frame as a base64-encoded JPEG.
        @return str or None.
        """
        with self._lock:
            return self._last_encoded_image
