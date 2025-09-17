from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from .controllers.social_fsm import SocialFSM
from .services.movement_service import MovementService
from .services.vision_service import VisionService


CONFIG_PATH = str(Path(__file__).resolve().parent / "config" / "app.json")


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
    ws_cfg: Dict[str, Any] = field(default_factory=dict)
    ws: Optional[Any] = None
    vision: Optional[VisionService] = None
    movement: Optional[MovementService] = None
    fsm: Optional[SocialFSM] = None


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def build(config_path: str = CONFIG_PATH) -> AppServices:
    """Build :class:`AppServices` instances from a configuration file."""

    cfg: Dict[str, Any] = {}
    if config_path:
        cfg = _load_json(config_path)

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

    ws_cfg = cfg.get("ws", {}) or {}
    services.ws_cfg = {
        "host": ws_cfg.get("host", "0.0.0.0"),
        "port": int(ws_cfg.get("port", 8765)),
    }
    services.ws = None

    if services.enable_vision:
        vision = VisionService(
            mode=services.mode,
            camera_fps=services.camera_fps,
            face_cfg=services.face_cfg,
        )
        if services.face_cfg:
            profile = str(services.face_cfg.get("profile", "face"))
            vision.register_face_pipeline(profile)
        services.vision = vision

    if services.enable_movement:
        services.movement = MovementService()

    if services.vision and services.movement:
        services.fsm = SocialFSM(services.vision, services.movement, cfg)

    return services
