from interface.base.movement_interface import IMovementController
import logging

logger = logging.getLogger(__name__)


class MockMovementController(IMovementController):
    """
    Simulated low-level controller for sandbox mode.
    Mirrors core.movement.controller.MovementController behavior conceptually.
    """

    def __init__(self):
        self.head_min_deg = -30.0
        self.head_max_deg = 30.0
        self.head_center_deg = 0.0

        # Define head_limits for compatibility with hardware-based controller
        self.head_limits = [
            self.head_min_deg,
            self.head_max_deg,
            self.head_center_deg,
        ]

        logger.debug(
            "[MOCK] MockMovementController created with head_limits "
            f"({self.head_limits[0]}, {self.head_limits[1]}, center={self.head_limits[2]})"
        )

    def move_head(self, x_deg: float, y_deg: float):
        logger.debug(f"[MOCK] move_head called: x={x_deg:.2f}, y={y_deg:.2f}")

    def relax(self):
        logger.debug("[MOCK] relax() called (simulated).")

    def start_loop(self):
        logger.debug("[MOCK] start_loop() called (simulated).")


class MockMovementService(IMovementController):
    """
    High-level mock equivalent to MovementControl for simulation.
    Provides mc (MovementController) and controller attributes for full API compatibility.
    """

    def __init__(self):
        # Create mock controller (matches MovementControl.mc)
        self.mc = MockMovementController()
        self.controller = self.mc  # alias for compatibility with MovementControl

        # Define compatible head limits
        self.head_limits = [
            self.mc.head_min_deg,
            self.mc.head_max_deg,
            self.mc.head_center_deg,
        ]

        logger.info(
            "[MOCK] MockMovementService initialized with head limits "
            f"({self.head_limits[0]}, {self.head_limits[1]}, center={self.head_limits[2]})"
        )

    def move_head(self, x_deg: float, y_deg: float):
        """Forward to low-level mock controller."""
        self.mc.move_head(x_deg, y_deg)

    def relax(self):
        self.mc.relax()

    def start_loop(self):
        self.mc.start_loop()
