"""Mock implementation of the movement subsystem."""
from __future__ import annotations

import logging


class MockMovementService:
    """Log-only replacement for :class:`app.services.movement_service.MovementService`."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("mock.movement")
        self._running = False
        self._relaxed = False
        # Provide an attribute compatible with the real service API
        self.mc: "MockMovementService" = self

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.logger.info("[MOCK] Movement started")

    def move(self, direction: str, speed: float) -> None:
        self.logger.info("[MOCK] Moving %s at speed %.2f", direction, speed)
        self._relaxed = False

    def relax(self) -> None:
        self.logger.info("[MOCK] Movement relaxed")
        self._relaxed = True

    def stop(self) -> None:
        if not self._running and self._relaxed:
            return
        self.logger.info("[MOCK] Movement stopped")
        self._running = False
        self._relaxed = True

    # Compatibility helpers -------------------------------------------------
    def turn_left(self, duration_ms: int, speed: float) -> None:  # pragma: no cover - shim
        self.logger.info("[MOCK] Turning left for %d ms at %.2f", duration_ms, speed)

    def turn_right(self, duration_ms: int, speed: float) -> None:  # pragma: no cover - shim
        self.logger.info("[MOCK] Turning right for %d ms at %.2f", duration_ms, speed)

    def start_loop(self) -> None:  # pragma: no cover - shim
        self.logger.debug("[MOCK] Movement control loop would run here")

    def stop_loop(self) -> None:  # pragma: no cover - shim
        self.logger.debug("[MOCK] Movement control loop stopped")
