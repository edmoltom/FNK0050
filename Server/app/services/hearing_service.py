from __future__ import annotations

"""Orchestration helpers for the hearing subsystem."""

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from core.hearing.stt import SpeechToText


class HearingService:
    """Thin wrapper around :class:`SpeechToText`."""

    def __init__(self, stt: "SpeechToText", *, enable_logging: bool = False) -> None:
        self._stt = stt
        self._thread: threading.Thread | None = None
        self._running = False
        self._log = logging.getLogger(__name__) if enable_logging else None

    def start(self) -> None:
        """Start background listening (discovers phrases but discards them)."""
        if self._running:
            return
        self._running = True
        if self._log:
            self._log.debug("Starting hearing service")

        def _drain() -> None:
            try:
                for _ in self._stt.listen():
                    if not self._running:
                        break
            finally:
                self._running = False

        self._thread = threading.Thread(target=_drain, daemon=True)
        self._thread.start()

    def update(self) -> None:
        """Periodic update hook (currently unused)."""
        return None

    def stop(self) -> None:
        """Stop background listening."""
        self._running = False
        if self._log:
            self._log.debug("Stopping hearing service")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.1)
