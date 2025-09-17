from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .services.vision_service import VisionService
from .services.movement_service import MovementService
from .controllers.social_fsm import SocialFSM


@dataclass
class AppServices:
    """Container for the services used by the application runtime."""

    cfg: Dict[str, Any] = field(default_factory=dict)
    vision_cfg: Dict[str, Any] = field(default_factory=dict)
    mode: str = "object"
    camera_fps: float = 15.0
    face_cfg: Dict[str, Any] = field(default_factory=dict)
    interval_sec: float = 1.0
    enable_vision: bool = True
    enable_movement: bool = True
    enable_ws: bool = True
    vision: Optional[VisionService] = None
    movement: Optional[MovementService] = None
    fsm: Optional[SocialFSM] = None


class AppBuilder:
    """Builds application services from a configuration dictionary."""

    def __init__(self, cfg: Optional[Dict[str, Any]] = None) -> None:
        self._cfg = cfg or {}

    def build(self) -> AppServices:
        cfg = self._cfg or {}
        services = AppServices()
        services.cfg = cfg

        services.enable_vision = bool(cfg.get("enable_vision", True))
        services.enable_ws = bool(cfg.get("enable_ws", True))
        services.enable_movement = bool(cfg.get("enable_movement", True))

        vision_cfg = cfg.get("vision", {}) or {}
        services.vision_cfg = vision_cfg
        services.mode = vision_cfg.get("mode", "object")
        services.camera_fps = float(vision_cfg.get("camera_fps", 15.0))
        services.face_cfg = vision_cfg.get("face", {}) or {}
        services.interval_sec = float(vision_cfg.get("interval_sec", 1.0))

        if services.enable_vision:
            services.vision = VisionService(
                mode=services.mode,
                camera_fps=services.camera_fps,
                face_cfg=services.face_cfg,
            )

        if services.enable_movement:
            services.movement = MovementService()

        if services.vision and services.movement:
            services.fsm = SocialFSM(services.vision, services.movement, cfg)

        return services
