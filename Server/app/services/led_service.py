from __future__ import annotations

"""Orchestration helpers for the LED subsystem."""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from core.LedController import LedController


class LedService:
    """Service wrapper around :class:`LedController`."""

    def __init__(
        self, controller: "LedController", *, enable_logging: bool = False
    ) -> None:
        self._controller = controller
        self._log = logging.getLogger(__name__) if enable_logging else None

    def start(self) -> None:
        """Initialize the LED subsystem (no-op)."""
        if self._log:
            self._log.debug("Starting LED service")
        return None

    def update(self) -> None:
        """Periodic update hook (currently unused)."""
        return None

    def stop(self) -> None:
        """Close the LED controller and release resources."""
        if self._log:
            self._log.debug("Stopping LED service")
        try:
            asyncio.run(self._controller.close())
        except Exception:
            pass
