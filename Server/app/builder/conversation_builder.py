"""Helpers for building conversation-related services."""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Callable, Dict, Optional, Tuple


__all__ = [
    "_build_conversation_llm_client",
    "_build_conversation_process",
    "_build_conversation_stt_service",
    "_build_conversation_tts",
    "_build_conversation_led_handler",
    "_build_conversation_manager_factory",
]


def _build_conversation_llm_client(cfg: Dict[str, Any]) -> Any:
    from mind.llm.client import LlamaClient

    return LlamaClient(
        base_url=cfg.get("llm_base_url") or None,
        request_timeout=cfg.get("llm_request_timeout"),
    )


def _build_conversation_process(cfg: Dict[str, Any]) -> Any:
    from mind.llm.process import LlamaServerProcess

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
    from interface.VoiceInterface import STTService
    from core.hearing.stt import SpeechToText

    stt_engine = SpeechToText()
    return STTService(stt_engine)


def _build_conversation_tts(_cfg: Dict[str, Any]) -> Any:
    from core.voice.tts import TextToSpeech

    return TextToSpeech()


def _build_conversation_led_handler(
    _cfg: Dict[str, Any]
) -> Tuple[Any, Callable[[], None]]:
    from interface.LedController import LedController
    from interface.VoiceInterface import LedStateHandler

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
    from interface.VoiceInterface import ConversationManager

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
