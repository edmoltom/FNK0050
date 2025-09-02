from __future__ import annotations

"""Orchestration helpers for the movement subsystem."""

import logging
from core.MovementControl import MovementControl


class MovementService:
    """Dispatch high-level commands to :class:`MovementControl`."""

    def __init__(
        self, controller: MovementControl, *, enable_logging: bool = False
    ) -> None:
        self._controller = controller
        self._log = logging.getLogger(__name__) if enable_logging else None

    def start(self) -> None:
        """Initialize the movement controller."""
        if self._log:
            self._log.debug("Starting movement service")
        # No explicit start sequence required; placeholder for future use.
        return None

    def update(self) -> None:
        """Process queued movement commands."""
        self._controller.tick(0.0)

    def stop(self) -> None:
        """Stop any ongoing motion."""
        if self._log:
            self._log.debug("Stopping movement service")
        try:
            self._controller.stop()
        except Exception:
            pass

    def walk(self, vx: float, vy: float, omega: float) -> None:
        """Delegate walking velocity commands to the controller."""
        self._controller.walk(vx, vy, omega)
