"""Public interface for the :mod:`app.builder` package."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

from . import core_builder as _core_builder


class _BuilderModule(ModuleType):
    """Module proxy that keeps :mod:`core_builder` in sync."""

    def __setattr__(self, name: str, value: Any) -> None:  # pragma: no cover - trivial
        setattr(_core_builder, name, value)
        super().__setattr__(name, value)


_module = sys.modules[__name__]
_module.__class__ = _BuilderModule
_module.__dict__.update(
    CONFIG_PATH=_core_builder.CONFIG_PATH,
    AppServices=_core_builder.AppServices,
    build=_core_builder.build,
    _build_conversation_llm_client=_core_builder._build_conversation_llm_client,
    _build_conversation_process=_core_builder._build_conversation_process,
    _build_conversation_stt_service=_core_builder._build_conversation_stt_service,
    _build_conversation_tts=_core_builder._build_conversation_tts,
    _build_conversation_led_handler=_core_builder._build_conversation_led_handler,
    _build_conversation_manager_factory=_core_builder._build_conversation_manager_factory,
)

__all__ = [
    "AppServices",
    "build",
    "CONFIG_PATH",
    "_build_conversation_llm_client",
    "_build_conversation_process",
    "_build_conversation_stt_service",
    "_build_conversation_tts",
    "_build_conversation_led_handler",
    "_build_conversation_manager_factory",
]
