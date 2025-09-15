from __future__ import annotations
from typing import Dict, List, Optional
import logging
import time

from .face_tracker import FaceTracker
from ..services.movement_service import MovementService
from ..services.vision_service import VisionService


class SocialFSM:
    """Simple social finite state machine based on face alignment."""

    def __init__(self, vision: VisionService, movement: MovementService, cfg: dict | None = None) -> None:
        cfg = cfg or {}
        behavior_cfg = cfg.get("behavior", {}).get("social_fsm", {})
        self.deadband_x = float(behavior_cfg.get("deadband_x", 0.12))
        self.lock_frames_needed = int(behavior_cfg.get("lock_frames_needed", 3))
        self.miss_release = int(behavior_cfg.get("miss_release", 5))
        self.interact_ms = int(behavior_cfg.get("interact_ms", 1500))
        self.relax_timeout = float(behavior_cfg.get("relax_timeout", 30.0))

        self.vision = vision
        self.movement = movement
        self.tracker = FaceTracker(movement.mc, vision.vm)
        # Keep deadband consistent with the tracker so state decisions match
        self.tracker.deadband_x = self.deadband_x

        self.state = "IDLE"
        self.miss_frames = 0
        self.lock_frames = 0
        self.interact_until = 0.0
        self.last_active = time.monotonic()

        self.logger = logging.getLogger("social_fsm")
        self.audio = None

    def _set_state(self, new_state: str) -> None:
        if new_state == self.state:
            return
        self.logger.info("leaving %s", self.state)
        self.state = new_state
        self.logger.info("entering %s", self.state)
        if new_state == "INTERACT":
            self.interact_until = time.monotonic() + self.interact_ms / 1000.0
            self._on_interact()
        if new_state != "INTERACT":
            self.lock_frames = 0

    def on_frame(self, result: Dict | None, dt: float) -> None:
        self.tracker.update(result, dt)

        faces = result.get("faces") if result else None
        face = self._select_largest_face(faces) if faces else None
        space_w = 0.0
        if result:
            space = result.get("space", (0, 0))
            if len(space) > 0:
                space_w = float(space[0])
        ex = self._ex_from_face(face, space_w) if face else 0.0

        now = time.monotonic()
        if face:
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
            if abs(ex) > self.deadband_x:
                self.lock_frames = 0
                if not hasattr(self, "_drift_until"):
                    self._drift_until = now + 0.4
                if now >= self._drift_until:
                    self._set_state("ALIGNING")
            else:
                self._drift_until = None
            return

        if not face:
            if self.miss_frames >= self.miss_release:
                self._set_state("IDLE")
        else:
            if self.state == "IDLE":
                self._set_state("ALIGNING")
            if abs(ex) <= self.deadband_x:
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

    def _select_largest_face(self, faces: List[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if not faces:
            return None
        return max(faces, key=lambda f: float(f.get("w", 0.0)) * float(f.get("h", 0.0)))

    def _ex_from_face(self, face: Dict[str, float], space_w: float) -> float:
        x = float(face.get("x", 0.0))
        w = float(face.get("w", 0.0))
        face_center_x = x + w / 2.0
        return (face_center_x - space_w / 2.0) / (space_w / 2.0) if space_w > 0 else 0.0

    def _on_interact(self) -> None:
        self.last_active = time.monotonic()
        if getattr(self, "audio", None):
            try:
                self.audio.play("meow1.wav")
            except Exception:
                logging.info("meow")
        else:
            logging.info("meow")
