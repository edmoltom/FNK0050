"""Mock implementation of the :mod:`app.services.vision_service` API."""
from __future__ import annotations

import logging
import random
import threading
import time
from typing import Callable, Dict, Optional


class MockVisionService:
    """Simulate the behaviour of ``VisionService`` without hardware access."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("mock.vision")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_callback: Optional[Callable[[Dict[str, float]], None]] = None
        self._latest_frame: Dict[str, float] = {}
        self._lock = threading.Lock()

    def set_frame_callback(
        self, callback: Optional[Callable[[Dict[str, float] | None], None]]
    ) -> None:
        """Register a callback to be invoked for every simulated frame."""

        self._frame_callback = callback

    def start(
        self,
        interval_sec: float = 1.0,
        frame_handler: Optional[Callable[[Dict[str, float] | None], None]] = None,
    ) -> None:
        """Start emitting simulated detections at the requested interval."""

        if self._running:
            return

        self._frame_callback = frame_handler or self._frame_callback
        self._running = True
        self.logger.debug("[MOCK] Vision started")

        interval = max(0.05, float(interval_sec or 0.0))
        thread = threading.Thread(
            target=self._run_loop, args=(interval,), name="mock-vision", daemon=True
        )
        self._thread = thread
        thread.start()

    def _run_loop(self, interval: float) -> None:
        while self._running:
            frame = self.get_latest_frame()
            callback = self._frame_callback
            if callback:
                try:
                    callback(frame)
                except Exception:
                    self.logger.exception("Mock vision callback failed")
            time.sleep(interval)

    def get_latest_frame(self) -> Dict[str, float]:
        """Return a fake face detection dictionary."""

        face_detected = random.random() > 0.2
        detection = {
            "face_detected": face_detected,
            "x": 320.0 + random.uniform(-25.0, 25.0),
            "y": 240.0 + random.uniform(-25.0, 25.0),
        }
        with self._lock:
            self._latest_frame = detection
        self.logger.debug("[MOCK] Vision frame generated: %s", detection)
        return dict(detection)

    def stop(self) -> None:
        if not self._running:
            self.logger.debug("[MOCK] Vision stopped")
            return
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        self.logger.debug("[MOCK] Vision stopped")

    # Compatibility helpers -------------------------------------------------
    @property
    def vm(self) -> "MockVisionService":  # pragma: no cover - simple shim
        """Provide a stand-in attribute expected by :class:`SocialFSM`."""

        return self
