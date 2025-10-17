"""Mock implementation of the movement subsystem."""
from __future__ import annotations

import logging

from interface.base.movement_interface import IMovementController

logger = logging.getLogger(__name__)


class MockMovementService(IMovementController):
    """Mocked movement controller for simulation mode."""

    def __init__(self):
        self.head_limits = [-30.0, 30.0, 0.0]
        logger.info("[MOCK] Using default head_limits [-30, 30, 0].")
        logger.info(f"[MOVEMENT] Controller initialized ({self.__class__.__name__})")

    def move_head(self, x_deg: float, y_deg: float):
        logger.debug(f"[MOCK] move_head called: x={x_deg}, y={y_deg}")

    def relax(self):
        logger.debug("[MOCK] relax() called")

    def start_loop(self):
        logger.debug("[MOCK] start_loop() called")
