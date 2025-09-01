from __future__ import annotations

"""Main application coordinating high-level subsystems."""

from core.VisionInterface import VisionInterface
from core.MovementControl import MovementControl

from .config import AppConfig, load_config
from .services.vision_service import VisionService
from .services.movement_service import MovementService


class Application:
    """Container object wiring core interfaces with their services."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()

        self.vision_service: VisionService | None = None
        if self.config.vision.enable:
            self.vision = VisionInterface()
            self.vision.set_mode(self.config.vision.profile)
            self.vision.set_processing_config(
                {
                    "threshold": self.config.vision.threshold,
                    "model_path": self.config.vision.model_path,
                }
            )
            self.vision_service = VisionService(self.vision)
        else:
            self.vision = None

        self.movement_service: MovementService | None = None
        if self.config.movement.enable:
            self.movement = MovementControl()
            self.movement_service = MovementService(self.movement)
        else:
            self.movement = None

    def run(self) -> None:
        """Start subsystems and keep the main loop alive."""
        if self.vision_service:
            self.vision_service.start()
        if self.movement_service:
            self.movement_service.start()

        try:
            while True:
                if self.vision_service:
                    self.vision_service.update()
                if self.movement_service:
                    self.movement_service.update()
        except KeyboardInterrupt:
            pass
        finally:
            if self.movement_service:
                self.movement_service.stop()
            if self.vision_service:
                self.vision_service.stop()
