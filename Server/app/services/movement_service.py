from __future__ import annotations

"""Orchestration helpers for the movement subsystem."""

from core.MovementControl import MovementControl


class MovementService:
    """Dispatch high-level commands to :class:`MovementControl`."""

    def __init__(self, controller: MovementControl) -> None:
        self._controller = controller

    def start(self) -> None:
        """Initialize the movement controller."""
        # No explicit start sequence required; placeholder for future use.
        return None

    def update(self) -> None:
        """Process queued movement commands."""
        self._controller.tick(0.0)

    def stop(self) -> None:
        """Stop any ongoing motion."""
        try:
            self._controller.stop()
        except Exception:
            pass

    def walk(self, vx: float, vy: float, omega: float) -> None:
        """Delegate walking velocity commands to the controller."""
        self._controller.walk(vx, vy, omega)
