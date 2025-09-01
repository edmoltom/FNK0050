from __future__ import annotations

"""Main application coordinating high-level subsystems."""

from core.VisionInterface import VisionInterface
from core.MovementControl import MovementControl

from .services.vision_service import VisionService
from .services.movement_service import MovementService


class Application:
    """Container object wiring core interfaces with their services."""

    def __init__(self) -> None:
        self.vision = VisionInterface()
        self.movement = MovementControl()

        self.vision_service = VisionService(self.vision)
        self.movement_service = MovementService(self.movement)

    def run(self) -> None:
        """Start subsystems and keep the main loop alive."""
        self.vision_service.start()
        self.movement_service.start()

        try:
            while True:
                self.vision_service.update()
                self.movement_service.update()
        except KeyboardInterrupt:
            pass
        finally:
            self.movement_service.stop()
            self.vision_service.stop()
