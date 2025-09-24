from __future__ import annotations

import json
import logging

import asyncio
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple


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


def _build_conversation_llm_client(cfg: Dict[str, Any]) -> Any:
    from core.llm.llm_client import LlamaClient

    return LlamaClient(
        base_url=cfg.get("llm_base_url") or None,
        request_timeout=cfg.get("llm_request_timeout"),
    )


def _build_conversation_process(cfg: Dict[str, Any]) -> Any:
    from core.llm.llama_server_process import LlamaServerProcess

    threads = cfg.get("threads") or None
    parallel = cfg.get("max_parallel_inference") or None

    return LlamaServerProcess(
        cfg["llama_binary"],
        cfg["model_path"],
        port=int(cfg.get("port", 0)),
        threads=threads,
        parallel=parallel,
    )


def _build_conversation_stt_service(_cfg: Dict[str, Any]) -> Any:
    from core.VoiceInterface import STTService
    from core.hearing.stt import SpeechToText

    stt_engine = SpeechToText()
    return STTService(stt_engine)


def _build_conversation_tts(_cfg: Dict[str, Any]) -> Any:
    from core.voice.tts import TextToSpeech

    return TextToSpeech()


def _build_conversation_led_handler(
    _cfg: Dict[str, Any]
) -> Tuple[Any, asyncio.AbstractEventLoop, threading.Thread]:
    from LedController import LedController
    from core.VoiceInterface import LedStateHandler

    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    controller = LedController(loop=loop)
    handler = LedStateHandler(controller, loop, loop_thread=loop_thread)
    return handler, loop, loop_thread


def _build_conversation_manager_factory() -> Tuple[
    Callable[..., Any],
    Dict[str, Any],
    Callable[[threading.Event], None],
]:
    from core.VoiceInterface import ConversationManager

    stop_event_ref: Dict[str, threading.Event] = {}

    def _register(event: threading.Event) -> None:
        stop_event_ref["stop_event"] = event

    def _factory(
        *,
        stt: Any,
        tts: Any,
        led_controller: Any,
        llm_client: Any,
        wait_until_ready: Callable[[], None],
        additional_stop_events: Optional[Tuple[threading.Event, ...]] = None,
    ) -> Any:
        stop_event = stop_event_ref.get("stop_event")
        if stop_event is None:
            raise RuntimeError("Conversation stop event not registered")
        return ConversationManager(
            stt=stt,
            tts=tts,
            led_controller=led_controller,
            llm_client=llm_client,
            stop_event=stop_event,
            wait_until_ready=wait_until_ready,
            additional_stop_events=additional_stop_events,
        )

    manager_kwargs: Dict[str, Any] = {"wait_until_ready": lambda: None}
    return _factory, manager_kwargs, _register


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
        "health_check_interval": 0.5,
        "health_check_max_retries": 3,
        "health_check_backoff": 2.0,
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
    merged_conversation_cfg["health_check_interval"] = float(
        merged_conversation_cfg.get(
            "health_check_interval", conversation_defaults["health_check_interval"]
        )
    )
    merged_conversation_cfg["health_check_max_retries"] = int(
        merged_conversation_cfg.get(
            "health_check_max_retries", conversation_defaults["health_check_max_retries"]
        )
    )
    merged_conversation_cfg["health_check_backoff"] = float(
        merged_conversation_cfg.get(
            "health_check_backoff", conversation_defaults["health_check_backoff"]
        )
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
    services.conversation = None
    fsm_callbacks: Dict[str, Callable[[Any], None]] = {}

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
        from .services.conversation_service import ConversationService

        llm_client = _build_conversation_llm_client(services.conversation_cfg)
        llama_process = _build_conversation_process(services.conversation_cfg)
        stt_service = _build_conversation_stt_service(services.conversation_cfg)
        tts_engine = _build_conversation_tts(services.conversation_cfg)
        led_handler, _, _ = _build_conversation_led_handler(services.conversation_cfg)
        manager_factory, manager_kwargs, register_stop_event = _build_conversation_manager_factory()

        readiness_timeout = services.conversation_cfg.get("health_timeout", 5.0)

        conversation_service = ConversationService(
            stt=stt_service,
            tts=tts_engine,
            led_controller=led_handler,
            llm_client=llm_client,
            process=llama_process,
            manager_factory=manager_factory,
            manager_kwargs=manager_kwargs,
            readiness_timeout=readiness_timeout,
        )
        register_stop_event(conversation_service.stop_event)
        services.conversation = conversation_service

        def _on_interact(_fsm: Any) -> None:
            conversation_service.start()

        def _on_exit_interact(_fsm: Any) -> None:
            conversation_service.stop()

        fsm_callbacks = {
            "on_interact": _on_interact,
            "on_exit_interact": _on_exit_interact,
        }

    if services.vision and services.movement:
        from .controllers.social_fsm import SocialFSM

        callbacks = fsm_callbacks or None
        services.fsm = SocialFSM(services.vision, services.movement, cfg, callbacks=callbacks)

    return services
