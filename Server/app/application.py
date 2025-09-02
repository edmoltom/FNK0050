from __future__ import annotations

"""Main application coordinating high-level subsystems."""

import logging

from core.VisionInterface import VisionInterface
from core.MovementControl import MovementControl
from core.vision.viz_logger import create_logger as create_vision_logger
from core.movement.logger import MovementLogger

from .config import AppConfig, load_config
from .services import (
    VisionService,
    MovementService,
    VoiceService,
    LedService,
    HearingService,
)


class Application:
    """Container object wiring core interfaces with their services."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()

        # Configure global logging level
        if self.config.logging.enable:
            level = getattr(logging, self.config.logging.level.upper(), logging.INFO)
            logging.basicConfig(level=level)

        self.vision_service: VisionService | None = None
        if self.config.vision.enable:
            vision_logger = create_vision_logger(enable=self.config.logging.vision)
            self.vision = VisionInterface(logger=vision_logger)
            self.vision.set_mode(self.config.vision.profile)
            self.vision.set_processing_config(
                {
                    "threshold": self.config.vision.threshold,
                    "model_path": self.config.vision.model_path,
                }
            )
            self.vision_service = VisionService(
                self.vision, enable_logging=self.config.logging.vision
            )
        else:
            self.vision = None

        self.movement_service: MovementService | None = None
        if self.config.movement.enable:
            mv_logger = MovementLogger() if self.config.logging.movement else None
            self.movement = MovementControl(logger=mv_logger)
            self.movement_service = MovementService(
                self.movement, enable_logging=self.config.logging.movement
            )
        else:
            self.movement = None

        self.voice_service: VoiceService | None = None
        if self.config.voice.enable:
            try:
                from core.VoiceInterface import ConversationManager

                self.voice = ConversationManager()
                self.voice_service = VoiceService(
                    self.voice, enable_logging=self.config.logging.voice
                )
            except Exception as exc:  # pragma: no cover - best effort
                logging.getLogger(__name__).warning(
                    "Voice subsystem unavailable: %s", exc
                )
                self.voice = None
        else:
            self.voice = None

        self.led_service: LedService | None = None
        if self.config.led.enable:
            try:
                from core.LedController import LedController

                self.led = LedController()
                self.led_service = LedService(
                    self.led, enable_logging=self.config.logging.led
                )
            except Exception as exc:  # pragma: no cover
                logging.getLogger(__name__).warning(
                    "LED subsystem unavailable: %s", exc
                )
                self.led = None
        else:
            self.led = None

        self.hearing_service: HearingService | None = None
        if self.config.hearing.enable:
            try:
                from core.hearing.stt import SpeechToText

                self.hearing = SpeechToText()
                self.hearing_service = HearingService(
                    self.hearing, enable_logging=self.config.logging.hearing
                )
            except Exception as exc:  # pragma: no cover
                logging.getLogger(__name__).warning(
                    "Hearing subsystem unavailable: %s", exc
                )
                self.hearing = None
        else:
            self.hearing = None

    def run(self) -> None:
        """Start subsystems and keep the main loop alive."""
        if self.vision_service:
            self.vision_service.start()
        if self.movement_service:
            self.movement_service.start()
        if self.voice_service:
            self.voice_service.start()
        if self.led_service:
            self.led_service.start()
        if self.hearing_service:
            self.hearing_service.start()

        try:
            while True:
                if self.vision_service:
                    self.vision_service.update()
                if self.movement_service:
                    self.movement_service.update()
                if self.voice_service:
                    self.voice_service.update()
                if self.led_service:
                    self.led_service.update()
                if self.hearing_service:
                    self.hearing_service.update()
        except KeyboardInterrupt:
            pass
        finally:
            if self.hearing_service:
                self.hearing_service.stop()
            if self.led_service:
                self.led_service.stop()
            if self.voice_service:
                self.voice_service.stop()
            if self.movement_service:
                self.movement_service.stop()
            if self.vision_service:
                self.vision_service.stop()
