"""High-level orchestration for the mind package."""

from __future__ import annotations

import logging
from typing import Any, Optional

from mind.behavior.social_fsm import SocialFSM
from mind.proprioception.body_model import BodyModel

logger = logging.getLogger(__name__)


class MindSupervisor:
    """High-level orchestration of Lumo's cognitive and social behavior."""

    def __init__(
        self,
        *,
        vision: Any | None = None,
        voice: Any | None = None,
        movement: Any | None = None,
        social: SocialFSM | None = None,
    ) -> None:
        self.body = BodyModel()
        self.vision = vision
        self.voice = voice
        self.movement = movement
        self.social: Optional[SocialFSM] = social
        if self.social is None and vision is not None and movement is not None:
            self.social = SocialFSM(vision, movement)
            logger.info("[MIND] SocialFSM wired to supervisor.")
        self.state = "BOOT"
        logger.info("[MIND] Supervisor initialized.")

    # ------------------------------------------------------------------
    # Wiring helpers
    # ------------------------------------------------------------------
    def attach_interfaces(
        self,
        *,
        vision: Any | None = None,
        voice: Any | None = None,
        movement: Any | None = None,
        social: SocialFSM | None = None,
    ) -> None:
        """Bind runtime interfaces after initialization."""

        if vision is not None:
            self.vision = vision
        if voice is not None:
            self.voice = voice
        if movement is not None:
            self.movement = movement
        if social is not None:
            self.social = social

        if self.vision is not None and self.movement is not None:
            if self.social is None:
                self.social = SocialFSM(self.vision, self.movement)
                logger.info("[MIND] SocialFSM wired to supervisor.")
            else:
                # The FSM keeps internal references, so rebuild if instances change.
                if (
                    getattr(self.social, "vision", None) is not self.vision
                    or getattr(self.social, "movement", None) is not self.movement
                ):
                    self.social = SocialFSM(self.vision, self.movement)
                    logger.info("[MIND] SocialFSM reconfigured for new interfaces.")

    # ------------------------------------------------------------------
    # Main reasoning loop
    # ------------------------------------------------------------------
    def update(self) -> None:
        """Main reasoning loop – decides what to activate at each cycle."""

        try:
            speaking = False
            if self.voice and hasattr(self.voice, "is_speaking"):
                try:
                    speaking = bool(self.voice.is_speaking())
                except Exception:  # pragma: no cover - defensive
                    logger.debug("[MIND] Voice subsystem failed while checking speech state.", exc_info=True)

            if speaking:
                if self.social and hasattr(self.social, "pause"):
                    self.social.pause()
                relax_body = getattr(self.body, "relax", None)
                if callable(relax_body):
                    relax_body()
                elif self.movement is not None:
                    relax_movement = getattr(self.movement, "relax", None)
                    if callable(relax_movement):
                        relax_movement()
            else:
                if self.social and hasattr(self.social, "resume"):
                    self.social.resume()
                updater = getattr(self.social, "update", None)
                if callable(updater):
                    updater()
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("[MIND] Supervisor update failed: %s", exc, exc_info=True)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def set_state(self, new_state: str) -> None:
        logger.info("[MIND] State change: %s -> %s", self.state, new_state)
        self.state = new_state
