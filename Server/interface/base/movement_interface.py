from abc import ABC, abstractmethod


class IMovementController(ABC):
    """
    Abstract base interface for movement controllers.

    Implementations may be hardware-backed or simulated.
    The interface ensures that higher layers (mind, perception)
    can use a consistent API regardless of the backend.
    """

    # Expected attribute
    head_limits: list[float]

    @abstractmethod
    def move_head(self, x_deg: float, y_deg: float):
        """Move the robot's head to the given angles in degrees."""
        pass

    @abstractmethod
    def relax(self):
        """Release servos and return to neutral posture."""
        pass

    @abstractmethod
    def start_loop(self):
        """Start any internal motion control loop (if applicable)."""
        pass
