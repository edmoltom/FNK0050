from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional


class BehaviorManager:
    def __init__(
        self,
        vision: Any,
        movement: Any,
        conversation: Any,
        social_fsm: Any,
        poll_interval: float = 0.5,
    ) -> None:
        self.vision = vision
        self.movement = movement
        self.conversation = conversation
        self.social_fsm = social_fsm
        self.poll_interval = max(0.0, float(poll_interval))

        self.logger = logging.getLogger("behavior.manager")
        self.current_mode = "BOOT"
        self.running = False

        self._thread: Optional[threading.Thread] = None
        self._face_tracking_enabled: Optional[bool] = None
        self._movement_relaxed = False

    def start(self) -> None:
        """Launches a background thread that periodically checks subsystem states
        and coordinates behavior accordingly."""

        if self.running:
            return

        self.running = True
        thread = threading.Thread(target=self._run_loop, name="behavior-manager", daemon=True)
        self._thread = thread
        thread.start()

    def _run_loop(self) -> None:
        while self.running:
            start = time.monotonic()
            try:
                self._coordinate_behavior()
            except Exception:  # pragma: no cover - defensive
                self.logger.exception("Behavior loop iteration failed")
            elapsed = time.monotonic() - start
            sleep_for = max(0.0, self.poll_interval - elapsed)
            time.sleep(sleep_for)

    def _coordinate_behavior(self) -> None:
        state = self._get_conversation_state()
        if state in {"THINK", "SPEAK"}:
            self._set_mode("CONVERSE")
            self._set_face_tracking(False)
            if hasattr(self.social_fsm, "pause"):
                self.social_fsm.pause()
            self._stop_motion()
        elif state in {"ATTENTIVE_LISTEN", "WAKE"}:
            self._set_mode("SOCIAL")
            self._set_face_tracking(True)
            if hasattr(self.social_fsm, "resume"):
                self.social_fsm.resume()
            if hasattr(self.social_fsm, "mute_social"):
                self.social_fsm.mute_social(True)
            self._movement_relaxed = False
        else:
            self._set_mode("IDLE")
            self._set_face_tracking(True)
            if hasattr(self.social_fsm, "resume"):
                self.social_fsm.resume()
            if hasattr(self.social_fsm, "mute_social"):
                self.social_fsm.mute_social(False)
            self._relax_movement()

    def _get_conversation_state(self) -> Optional[str]:
        conversation = self.conversation
        if not conversation:
            return None

        raw_state = getattr(conversation, "state", None)
        if raw_state is None:
            manager = getattr(conversation, "_manager", None)
            raw_state = getattr(manager, "state", None) if manager else None
        if isinstance(raw_state, str):
            return raw_state.upper()
        return None

    def _set_face_tracking(self, enabled: bool) -> None:
        if self._face_tracking_enabled is enabled:
            return

        tracker = getattr(getattr(self.social_fsm, "tracker", None), "set_enabled", None)
        if not callable(tracker):
            self._face_tracking_enabled = enabled
            return

        try:
            tracker(enabled)
        except Exception:  # pragma: no cover - defensive
            self.logger.exception("Failed to toggle face tracking to %s", enabled)
        finally:
            self._face_tracking_enabled = enabled

    def _stop_motion(self) -> None:
        controller = getattr(self.movement, "mc", self.movement)
        stop = getattr(controller, "stop", None)
        if not callable(stop):
            return
        try:
            stop()
        except Exception:  # pragma: no cover - defensive
            self.logger.exception("Failed to stop movement controller")
        self._movement_relaxed = False

    def _relax_movement(self) -> None:
        if self._movement_relaxed:
            return
        relax = getattr(self.movement, "relax", None)
        if not callable(relax):
            self._movement_relaxed = True
            return
        try:
            relax()
        except Exception:  # pragma: no cover - defensive
            self.logger.exception("Failed to relax movement controller")
        self._movement_relaxed = True

    def _set_mode(self, new_mode: str) -> None:
        if new_mode != self.current_mode:
            self.logger.info("Behavior mode: %s → %s", self.current_mode, new_mode)
            self.current_mode = new_mode
