from __future__ import annotations

"""Orchestration helpers for the voice subsystem."""

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from core.VoiceInterface import ConversationManager


class VoiceService:
    """Thin wrapper around :class:`ConversationManager`."""

    def __init__(
        self, interface: "ConversationManager", *, enable_logging: bool = False
    ) -> None:
        self._interface = interface
        self._thread: threading.Thread | None = None
        self._log = logging.getLogger(__name__) if enable_logging else None

    def start(self) -> None:
        """Launch the conversation manager in a background thread."""
        if self._log:
            self._log.debug("Starting voice service")
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._interface.run, daemon=True)
        self._thread.start()

    def update(self) -> None:
        """Periodic update hook (currently a no-op)."""
        return None

    def stop(self) -> None:
        """Stop the conversation manager if running."""
        if self._log:
            self._log.debug("Stopping voice service")
        # The underlying conversation loop has no explicit shutdown, so this
        # merely signals the thread to end when the loop finishes.
        return None
