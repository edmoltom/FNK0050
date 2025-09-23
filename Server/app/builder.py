from __future__ import annotations

import json
import logging

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


CONFIG_PATH = str(Path(__file__).resolve().parent / "config" / "app.json")


logger = logging.getLogger(__name__)


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
    enable_conversation: bool = False
    ws_cfg: Dict[str, Any] = field(default_factory=dict)
    conversation_cfg: Dict[str, Any] = field(default_factory=dict)
    ws: Optional[Any] = None
    vision: Optional[Any] = None
    movement: Optional[Any] = None
    conversation: Optional[Any] = None
    conversation_disabled_reason: Optional[str] = None
    fsm: Optional[Any] = None


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
    conversation_defaults = {
        "enable": False,
        "llama_binary": "",
        "model_path": "",
        "port": 9090,
        "threads": 2,
        "health_timeout": 5.0,
        "llm_base_url": "",
        "llm_request_timeout": 30.0,
        "max_parallel_inference": 1,
    }
    conversation_cfg_raw = cfg.get("conversation", {}) or {}
    merged_conversation_cfg: Dict[str, Any] = {**conversation_defaults, **conversation_cfg_raw}
    merged_conversation_cfg["enable"] = bool(merged_conversation_cfg.get("enable", False))
    merged_conversation_cfg["llama_binary"] = str(merged_conversation_cfg.get("llama_binary", ""))
    merged_conversation_cfg["model_path"] = str(merged_conversation_cfg.get("model_path", ""))
    merged_conversation_cfg["port"] = int(merged_conversation_cfg.get("port", conversation_defaults["port"]))
    merged_conversation_cfg["threads"] = int(merged_conversation_cfg.get("threads", conversation_defaults["threads"]))
    merged_conversation_cfg["health_timeout"] = float(
        merged_conversation_cfg.get("health_timeout", conversation_defaults["health_timeout"])
    )
    merged_conversation_cfg["llm_base_url"] = str(merged_conversation_cfg.get("llm_base_url", ""))
    merged_conversation_cfg["llm_request_timeout"] = float(
        merged_conversation_cfg.get(
            "llm_request_timeout", conversation_defaults["llm_request_timeout"]
        )
    )
    merged_conversation_cfg["max_parallel_inference"] = int(
        merged_conversation_cfg.get("max_parallel_inference", conversation_defaults["max_parallel_inference"])
    )

    services.conversation_cfg = merged_conversation_cfg
    services.enable_conversation = merged_conversation_cfg["enable"]
    services.conversation_disabled_reason = None

    required_paths = [
        key for key in ("llama_binary", "model_path") if not merged_conversation_cfg.get(key)
    ]
    if services.enable_conversation and required_paths:
        services.enable_conversation = False
        services.conversation_cfg["enable"] = False
        reason = (
            "Conversation disabled: missing required configuration values: "
            + ", ".join(required_paths)
        )
        services.conversation_disabled_reason = reason
        logger.debug(reason)
    services.ws = None

    if services.enable_vision:
        from .services.vision_service import VisionService

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
        from .services.movement_service import MovementService

        services.movement = MovementService()

    if services.enable_conversation and services.conversation_cfg["enable"]:
        from core.llm.llm_client import LlamaClient

        services.conversation = LlamaClient(
            base_url=services.conversation_cfg.get("llm_base_url") or None,
            request_timeout=services.conversation_cfg.get("llm_request_timeout"),
        )
    else:
        services.conversation = None

    if services.vision and services.movement:
        from .controllers.social_fsm import SocialFSM

        services.fsm = SocialFSM(services.vision, services.movement, cfg)

    return services
