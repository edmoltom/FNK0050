"""Mock LED controller that only logs colour changes."""
from __future__ import annotations

import logging


class MockLedController:
    """Simplified LED controller used in sandbox mode."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("mock.led")
        self._last_color: str | None = None

    def set_color(self, color: str) -> None:
        self._last_color = color
        self.logger.info("[MOCK-LED] color set to %s", color)

    # Compatibility helper --------------------------------------------------
    def set_state(self, state: str) -> None:  # pragma: no cover - compatibility
        """Mirror the interface expected by the real conversation LED handler."""

        self.logger.info("[MOCK-LED] state set to %s", state)
        self._last_color = state
