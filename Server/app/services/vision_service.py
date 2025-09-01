from __future__ import annotations

"""Orchestration helpers for the vision subsystem."""

from core.VisionInterface import VisionInterface


class VisionService:
    """Thin wrapper around :class:`VisionInterface`."""

    def __init__(self, vision: VisionInterface) -> None:
        self._vision = vision

    def start(self) -> None:
        """Begin periodic capture."""
        # Start background streaming to continually process frames.
        self._vision.start_stream()

    def update(self) -> None:
        """Hook for periodic tasks; currently a no-op."""
        return None

    def stop(self) -> None:
        """Stop any active streaming and release resources."""
        self._vision.stop()
