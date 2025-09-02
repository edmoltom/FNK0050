from __future__ import annotations

"""Orchestration helpers for the vision subsystem."""

import logging
import time
from typing import Generator, Optional

try:
    from Server.core.VisionInterface import VisionInterface
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    VisionInterface = object  # type: ignore[misc]


class VisionService:
    """Thin wrapper around :class:`VisionInterface`."""

    def __init__(self, vision: VisionInterface, *, enable_logging: bool = False) -> None:
        self._vision = vision
        self._log = logging.getLogger(__name__) if enable_logging else None

    def start(self, interval_sec: float = 1.0) -> None:
        """Begin periodic capture with optional interval."""
        # Start background streaming to continually process frames.
        if self._log:
            self._log.debug("Starting vision service")
        self._vision.start_stream(interval_sec=interval_sec)

    def update(self) -> None:
        """Hook for periodic tasks; currently a no-op."""
        return None

    def stop(self) -> None:
        """Stop any active streaming and release resources."""
        if self._log:
            self._log.debug("Stopping vision service")
        self._vision.stop()

    def get_last_processed_encoded(self):
        """Expose last processed frame."""
        return self._vision.get_last_processed_encoded()

    def stream(self, interval_sec: float = 0.05) -> Generator[Optional[str], None, None]:
        """Yield processed frames as they become available."""
        # ensure underlying vision subsystem is streaming
        if not getattr(self._vision, "_streaming", False):
            self._vision.start_stream(interval_sec=interval_sec)
        while getattr(self._vision, "_streaming", False):
            yield self._vision.get_last_processed_encoded()
            time.sleep(interval_sec)

    def set_processing_config(self, config: dict) -> None:
        """Forward runtime processing configuration."""
        self._vision.set_processing_config(config)
