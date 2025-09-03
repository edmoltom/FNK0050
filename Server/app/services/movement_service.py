from __future__ import annotations

import threading
from typing import Any, Optional

from core.MovementControl import MovementControl


class MovementService:
    """Service wrapper around :class:`MovementControl`."""

    def __init__(self, mc: Optional[MovementControl] = None) -> None:
        self.mc = mc or MovementControl()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        if not self._running:
            self._thread = threading.Thread(target=self.mc.start_loop, daemon=True)
            self._thread.start()
            self._running = True

    def stop(self) -> None:
        if self._running:
            self.mc.stop()
            self._running = False

    def relax(self) -> None:
        self.mc.relax()

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - simple delegation
        return getattr(self.mc, name)
