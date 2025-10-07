from __future__ import annotations
from typing import Callable, Dict, Optional
import logging
import time
import random
from pathlib import Path

from .face_tracker import FaceTracker
from ..services.movement_service import MovementService
from ..services.vision_service import VisionService
from core.voice.sfx import play_sound


class SocialFSM:
    """Simple social finite state machine based on face alignment."""

    def __init__(
        self,
        vision: VisionService,
        movement: MovementService,
        cfg: dict | None = None,
        callbacks: Optional[Dict[str, Callable[["SocialFSM"], None]]] = None,
    ) -> None:
        cfg = cfg or {}
        behavior_cfg = cfg.get("behavior", {}).get("social_fsm", {})
        self.deadband_x = float(behavior_cfg.get("deadband_x", 0.12))
        self.lock_frames_needed = int(behavior_cfg.get("lock_frames_needed", 3))
        self.miss_release = int(behavior_cfg.get("miss_release", 5))
        self.interact_ms = int(behavior_cfg.get("interact_ms", 1500))
        self.min_score = float(behavior_cfg.get("min_score", 0.0) or 0.0)
        self.cooldown = float(behavior_cfg.get("cooldown_ms", 0) or 0.0) / 1000.0
        self.relax_timeout = float(behavior_cfg.get("relax_timeout", 30.0))

        self.meow_cooldown_min = float(behavior_cfg.get("meow_cooldown_min", 5.0) or 5.0)
        self.meow_cooldown_max = float(behavior_cfg.get("meow_cooldown_max", 15.0) or 15.0)

        self.vision = vision
        self.movement = movement
        self.tracker = FaceTracker(movement.mc, vision.vm)
        # Keep deadband consistent with the tracker so state decisions match
        self.tracker.deadband_x = self.deadband_x
        self.tracker.lock_frames_needed = self.lock_frames_needed
        self.tracker.miss_release = self.miss_release
        recenter_after = behavior_cfg.get("recenter_after", 40)
        if recenter_after is not None:
            self.tracker.recenter_after = int(recenter_after)

        self.state = "IDLE"
        self.miss_frames = 0
        self.lock_frames = 0
        self.interact_until = 0.0
        self.last_active = time.monotonic()
        self._next_meow_time = 0.0

        self.logger = logging.getLogger("social_fsm")
        self.audio = None
        self._drift_until = None
        self.paused = False
        self.social_muted = False
        callbacks = dict(callbacks or {})
        disable_default = bool(callbacks.pop("disable_default_interact", False))
        self._callbacks: Dict[str, Callable[["SocialFSM"], None]] = {}
        for name in ("on_interact", "on_exit_interact"):
            cb = callbacks.get(name)
            if callable(cb):
                self._callbacks[name] = cb
        self._default_interact_enabled = not (
            disable_default and "on_interact" in self._callbacks
        )

    def _set_state(self, new_state: str) -> None:
        if new_state == self.state:
            return
        self.logger.info("[FSM] %s → %s", self.state, new_state)
        if self.state == "INTERACT":
            self._run_callback("on_exit_interact")
        self.state = new_state
        if new_state == "INTERACT":
            self.interact_until = time.monotonic() + self.interact_ms / 1000.0
            self._run_callback("on_interact")
            if self._default_interact_enabled:
                self._on_interact()
        if new_state != "INTERACT":
            self.lock_frames = 0
            self._drift_until = None

    def pause(self) -> None:
        """Temporarily suspend social reactions and movement updates."""

        self.paused = True
        self.logger.info("[FSM] paused")

    def resume(self) -> None:
        """Resume normal operation after a pause."""

        self.paused = False
        self.logger.info("[FSM] resumed")

    def mute_social(self, enabled: bool) -> None:
        """Enable or disable only the social reactions (e.g. meows) while keeping tracking active."""

        self.social_muted = enabled
        if enabled:
            self.logger.info("[FSM] social reactions muted")
        else:
            self.logger.info("[FSM] social reactions unmuted")

    def on_frame(self, result: Dict | None, dt: float) -> None:
        if self.paused:
            return

        detection = result or None
        if detection:
            score = float(detection.get("score") or 0.0)
            if score < self.min_score:
                detection = None

        self.tracker.update(detection, dt)

        has_target = bool(self.tracker.had_target)
        horizontal_error = self.tracker.horizontal_error if has_target else 0.0

        now = time.monotonic()
        if has_target:
            self.miss_frames = 0
            self.last_active = now
        else:
            self.miss_frames += 1
            self.lock_frames = 0
            if now - self.last_active > self.relax_timeout:
                self.movement.relax()
                self.last_active = now
        if self.state == "INTERACT":
            if self.miss_frames >= self.miss_release or now >= self.interact_until:
                self._set_state("IDLE")
                return
            if abs(horizontal_error) > self.deadband_x:
                self.lock_frames = 0
                if self._drift_until is None:
                    self._drift_until = now + 0.4
                if self._drift_until is not None and now >= self._drift_until:
                    self._set_state("ALIGNING")
            else:
                self._drift_until = None
            return

        if not has_target:
            if self.miss_frames >= self.miss_release:
                self._set_state("IDLE")
        else:
            if self.state == "IDLE":
                self._set_state("ALIGNING")
            if abs(horizontal_error) <= self.deadband_x:
                self.lock_frames += 1
                if self.lock_frames >= self.lock_frames_needed:
                    self._set_state("INTERACT")
            else:
                self.lock_frames = 0

        if self.state == "IDLE" and not getattr(self, "_idle_stopped", False):
            self.movement.stop()
            self._idle_stopped = True
        else:
            self._idle_stopped = False

    def _on_interact(self) -> None:
        now = time.monotonic()
        self.last_active = now
        if self.social_muted:
            return
        if now < self._next_meow_time:
            return
        sound_file = Path(__file__).resolve().parents[2] / "sounds" / "meow.wav"
        try:
            play_sound(sound_file)
        except Exception:
            self.logger.debug("meow")
        delay = random.uniform(self.meow_cooldown_min, self.meow_cooldown_max)
        self._next_meow_time = now + delay

    def _run_callback(self, name: str) -> None:
        callback = self._callbacks.get(name)
        if not callback:
            return
        try:
            callback(self)
        except Exception:
            self.logger.exception("error running %s callback", name)
