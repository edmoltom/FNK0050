from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from .builder import AppServices


class AppRuntime:
    """Coordinate application services during execution."""

    def __init__(self, services: AppServices) -> None:
        self.svcs = services
        self._latest_detection: Dict[str, Any] = {}
        self._frame_handler: Optional[Callable[[Dict[str, Any] | None], None]] = None

    @property
    def latest_detection(self) -> Dict[str, Any]:
        """Return a copy of the latest face detection."""
        return dict(self._latest_detection)

    @property
    def frame_handler(self) -> Optional[Callable[[Dict[str, Any] | None], None]]:
        return self._frame_handler

    def _store_latest_detection(self, result: Dict[str, Any] | None) -> None:
        self._latest_detection.clear()
        if result:
            self._latest_detection.update(result)

    def _register_frame_handler(self) -> None:
        prev_time = time.monotonic()

        def _handle(result: Dict[str, Any] | None) -> None:
            nonlocal prev_time
            now = time.monotonic()
            dt = now - prev_time
            prev_time = now

            if self.svcs.fsm:
                self.svcs.fsm.on_frame(result or {}, dt)

            self._store_latest_detection(result)

        self._frame_handler = _handle
