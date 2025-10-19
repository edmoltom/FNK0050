"""Interface-level module bridging mind and core layers."""

import base64
import threading
import time
import logging
from typing import Optional, TYPE_CHECKING, Callable, Tuple

import cv2

from core.vision import api
from core.vision.camera import Camera, CameraCaptureError
from core.vision.camera_worker import CameraWorker
from core.vision.overlays import draw_result, _get_reference_resolution
from core.vision.profile_manager import get_config

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from core.vision.viz_logger import VisionLogger


class VisionManager:
    """High-level vision manager backed by :class:`Camera` and vision ``api``."""

    def __init__(
        self,
        max_capture_failures: int = 3,
        camera: Optional[Camera] = None,
        logger: Optional['VisionLogger'] = None,
    ) -> None:
        self.camera = camera or Camera(max_failures=max_capture_failures)
        self._last_encoded_image: Optional[str] = None
        self._streaming = False
        self._thread: Optional[threading.Thread] = None
        self._worker: Optional[CameraWorker] = None
        self._lock = threading.Lock()
        self._mode: Optional[str] = None
        self._last_error: Optional[Exception] = None
        self._roi: Optional[Tuple[int, int, int, int]] = None

        self._logger: Optional['VisionLogger'] = logger or api.create_logger_from_env()
        self._py_logger = logging.getLogger("vision")

    # -------- Configuration API --------

    def register_pipeline(self, name: str, pipeline) -> None:
        """Register a new vision ``pipeline`` under ``name``."""
        api.register_pipeline(name, pipeline)

    def select_pipeline(self, name: str) -> None:
        """Select the active vision pipeline by ``name``."""
        self._mode = name
        api.select_pipeline(name)

    def set_roi(self, roi: Optional[Tuple[int, int, int, int]]) -> None:
        """Set ROI ``(x, y, w, h)`` for subsequent detections."""
        with self._lock:
            self._roi = roi

    def process(self, frame) -> dict:
        """Process a BGR ``frame`` using the active pipeline."""
        with self._lock:
            roi = self._roi
        cfg = {"roi": roi} if roi else None
        return api.process(frame, return_overlay=True, config=cfg)

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
        if self._worker:
            try:
                self._worker.stop()
            finally:
                self._worker.join(timeout=1.0)
            self._worker = None
        else:
            self.camera.stop()
        if self._logger:
            self._logger.close()

    # -------- Internal helpers --------

    def _apply_pipeline(self):
        frame_rgb = self.camera.capture_rgb()
        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        with self._lock:
            roi = self._roi
        cfg = {"roi": roi} if roi else None
        api.process(frame, return_overlay=True, config=cfg)
        if self._logger:
            self._logger.log(frame, result=api.get_last_result())
        frame = draw_result(frame, api.get_last_result())
        return frame

    # -------- Public API --------

    def start_stream(
        self,
        interval_sec: float = 1.0,
        on_frame: Optional[Callable[[dict | None], None]] = None,
    ) -> None:
        """Start periodic capture and processing in a background thread.

        The camera will be started automatically on the first call to
        :meth:`Camera.capture_rgb`, so invoking :meth:`start` beforehand is
        optional.  The method performs a guard start to ensure the device is
        ready.
        """
        if self._streaming:
            print("[VisionManager] Streaming already running.")
            return
        if not self.camera.is_running():
            self.camera.start()

        try:
            cv2.setNumThreads(1)
        except Exception:
            pass

        cfg = get_config("vision")
        camera_fps = float(cfg.get("camera_fps", 15.0))
        self._worker = CameraWorker(self.camera, max_fps=camera_fps)
        self._worker.start()
        self._streaming = True

        def _capture_loop():
            period = max(0.0, float(interval_sec))
            next_tick = time.monotonic()
            last_det = 0.0
            last_res = None
            det_times = []
            enc_times = []
            fps_samples = []
            roi_fracs = []
            last_frame_ts = None
            log_ts = time.monotonic()

            while self._streaming:
                start_tick = next_tick
                next_tick = start_tick + period
                try:
                    latest = self._worker.get_latest() if self._worker else None
                    now = time.time()
                    if latest and now - latest[1] <= 0.2:
                        frame_rgb, frame_ts = latest
                        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                        now_mono = time.monotonic()
                        if now_mono - last_det >= 0.2:
                            t0 = time.perf_counter()
                            with self._lock:
                                roi_cfg = {"roi": self._roi} if self._roi else None
                            api.process(frame, return_overlay=True, config=roi_cfg)
                            det_times.append(time.perf_counter() - t0)
                            last_res = api.get_last_result()
                            last_det = now_mono
                            if self._logger:
                                self._logger.log(frame, result=last_res)
                            if last_res:
                                data = last_res.data or {}
                                ref_w, ref_h = _get_reference_resolution(data)
                                roi = 0.0
                                if (
                                    "bbox" in data
                                    and isinstance(data["bbox"], (list, tuple))
                                    and len(data["bbox"]) == 4
                                ):
                                    _, _, w, h = data["bbox"]
                                    roi = (w * h) / (ref_w * ref_h)
                                elif data.get("faces"):
                                    area = 0.0
                                    for face in data.get("faces", []):
                                        fw = face.get("w")
                                        fh = face.get("h")
                                        if fw and fh:
                                            area += fw * fh
                                    if ref_w * ref_h > 0:
                                        roi = area / (ref_w * ref_h)
                                if roi:
                                    roi_fracs.append(roi)
                        frame = draw_result(frame, last_res)
                        t1 = time.perf_counter()
                        ok, buffer = cv2.imencode(".jpg", frame)
                        enc_times.append(time.perf_counter() - t1)
                        if ok:
                            encoded = base64.b64encode(buffer).decode("utf-8")
                            with self._lock:
                                self._last_encoded_image = encoded
                        if on_frame:
                            try:
                                on_frame(last_res.data if last_res else None)
                            except Exception as cb_exc:
                                print(f"[VisionManager] Frame callback error: {cb_exc}")
                        if last_frame_ts is not None:
                            dt = frame_ts - last_frame_ts
                            if dt > 0:
                                fps_samples.append(1.0 / dt)
                        last_frame_ts = frame_ts
                    else:
                        if on_frame and last_res:
                            try:
                                on_frame(last_res.data)
                            except Exception as cb_exc:
                                print(f"[VisionManager] Frame callback error: {cb_exc}")
                except CameraCaptureError as e:
                    print(f"[VisionManager] Capture error: {e}")
                    self._last_error = e
                    self._streaming = False
                    break
                except Exception as e:
                    print(f"[VisionManager] Error in periodic capture: {e}")
                now_mono2 = time.monotonic()
                if now_mono2 - log_ts >= 5.0:
                    avg_det = sum(det_times) / len(det_times) if det_times else 0.0
                    avg_enc = sum(enc_times) / len(enc_times) if enc_times else 0.0
                    avg_fps = sum(fps_samples) / len(fps_samples) if fps_samples else 0.0
                    avg_roi = sum(roi_fracs) / len(roi_fracs) if roi_fracs else 0.0
                    self._py_logger.info(
                        "det=%.1fms enc=%.1fms fps=%.2f roi=%.1f%%",
                        avg_det * 1000,
                        avg_enc * 1000,
                        avg_fps,
                        avg_roi * 100,
                    )
                    det_times.clear()
                    enc_times.clear()
                    fps_samples.clear()
                    roi_fracs.clear()
                    log_ts = now_mono2
                sleep_s = next_tick - time.monotonic()
                if sleep_s > 0:
                    time.sleep(sleep_s)
                else:
                    next_tick = time.monotonic()

        self._thread = threading.Thread(target=_capture_loop, daemon=True)
        self._thread.start()
        print("[VisionManager] Started stream thread.")

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
