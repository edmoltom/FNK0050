from __future__ import annotations

import json
import logging

import asyncio
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple


CONFIG_PATH = str(Path(__file__).resolve().parents[1] / "config" / "app.json")


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
) -> Tuple[Any, Callable[[], None]]:
    from LedController import LedController
    from core.VoiceInterface import LedStateHandler

    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    controller = LedController(loop=loop)
    handler = LedStateHandler(controller, loop, loop_thread=loop_thread)

    def _cleanup() -> None:
        try:
            handler.close()
        finally:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except RuntimeError:
                pass
            if loop_thread.is_alive():
                loop_thread.join(timeout=1)

    return handler, _cleanup


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
    **kwargs,
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
            **kwargs,
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
    missing_files: list[str] = []
    for key in ("llama_binary", "model_path"):
        value = merged_conversation_cfg.get(key)
        if not value:
            continue
        candidate = Path(str(value))
        if not candidate.exists():
            missing_files.append(f"{key}={candidate}")

    if services.enable_conversation and (required_paths or missing_files):
        services.enable_conversation = False
        services.conversation_cfg["enable"] = False
        reason_parts: list[str] = []
        if required_paths:
            reason_parts.append(
                "missing required configuration values: " + ", ".join(required_paths)
            )
        if missing_files:
            reason_parts.append("paths not found: " + ", ".join(missing_files))
        reason = "Conversation disabled: " + "; ".join(reason_parts)
        services.conversation_disabled_reason = reason
        if missing_files:
            logger.warning(
                "Conversation disabled: paths not found: llama_binary=%s, model_path=%s",
                services.conversation_cfg.get("llama_binary"),
                services.conversation_cfg.get("model_path"),
            )
        else:
            logger.warning(reason)
    services.ws = None
    services.conversation = None
    fsm_callbacks: Dict[str, Callable[[Any], None]] = {}

    if services.enable_vision:
        from app.services.vision_service import VisionService

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
        from app.services.movement_service import MovementService

        services.movement = MovementService()

    logger.info("Config conversation: %s", services.conversation_cfg)
    if not services.conversation_cfg["enable"]:
        logger.info("Conversation disabled by config flag")

    if services.enable_conversation and services.conversation_cfg["enable"]:
        from app.services.conversation_service import ConversationService

        try:
            llm_client = _build_conversation_llm_client(services.conversation_cfg)
            llama_process = _build_conversation_process(services.conversation_cfg)
            stt_service = _build_conversation_stt_service(services.conversation_cfg)
            tts_engine = _build_conversation_tts(services.conversation_cfg)
            led_handler, led_cleanup = _build_conversation_led_handler(
                services.conversation_cfg
            )
            (
                manager_factory,
                manager_kwargs,
                register_stop_event,
            ) = _build_conversation_manager_factory()
            logger.info("Conversation stop_event registered")

            readiness_timeout = services.conversation_cfg.get("health_timeout", 5.0)
            health_interval = services.conversation_cfg.get("health_check_interval", 0.5)
            health_retries = services.conversation_cfg.get("health_check_max_retries", 3)
            health_backoff = services.conversation_cfg.get("health_check_backoff", 2.0)
            health_base_url = services.conversation_cfg.get("llm_base_url") or None

            manager_kwargs = dict(manager_kwargs)
            manager_kwargs.setdefault("close_led_on_cleanup", False)

            conversation_service = ConversationService(
                stt=stt_service,
                tts=tts_engine,
                led_controller=led_handler,
                llm_client=llm_client,
                process=llama_process,
                manager_factory=manager_factory,
                manager_kwargs=manager_kwargs,
                readiness_timeout=readiness_timeout,
                health_check_base_url=health_base_url,
                health_check_interval=health_interval,
                health_check_max_retries=health_retries,
                health_check_backoff=health_backoff,
                health_check_timeout=readiness_timeout,
                led_cleanup=led_cleanup,
            )
            logger.info("ConversationService instance created successfully")
        except Exception:
            logger.exception("Failed to build ConversationService")
            raise

        register_stop_event(conversation_service.stop_event)
        services.conversation = conversation_service

        # The conversation service now runs independently of the FSM lifecycle.
        # It is started and stopped directly by the AppRuntime alongside the
        # rest of the services, so no FSM callbacks are required here.

    if services.vision and services.movement:
        from app.controllers.social_fsm import SocialFSM

        callbacks = fsm_callbacks or None
        services.fsm = SocialFSM(services.vision, services.movement, cfg, callbacks=callbacks)

    return services
