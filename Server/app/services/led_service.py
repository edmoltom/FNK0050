from __future__ import annotations

"""Orchestration helpers for the LED subsystem."""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from core.LedController import LedController


class LedService:
    """Service wrapper around :class:`LedController`."""

    def __init__(self, controller: "LedController") -> None:
        self._controller = controller

    def start(self) -> None:
        """Initialize the LED subsystem (no-op)."""
        return None

    def update(self) -> None:
        """Periodic update hook (currently unused)."""
        return None

    def stop(self) -> None:
        """Close the LED controller and release resources."""
        try:
            asyncio.run(self._controller.close())
        except Exception:
            pass
