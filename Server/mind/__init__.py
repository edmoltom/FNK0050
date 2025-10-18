"""The 'mind' package contains Lumo's cognitive and language modules.
It includes the LLM interface, memory systems, persona, and reasoning bridge.
"""

from typing import TYPE_CHECKING

__all__ = ["MindContext", "MindSupervisor", "initialize_mind"]

if TYPE_CHECKING:  # pragma: no cover
    from .context import MindContext as _MindContext
    from .supervisor import MindSupervisor as _MindSupervisor


def initialize_mind(
    config,
    *,
    vision=None,
    voice=None,
    movement=None,
    social=None,
):
    """Create and initialize the unified MindContext."""
    from .context import MindContext

    return MindContext(
        config,
        vision=vision,
        voice=voice,
        movement=movement,
        social=social,
    )


def __getattr__(name):
    if name == "MindContext":
        from .context import MindContext

        return MindContext
    if name == "MindSupervisor":
        from .supervisor import MindSupervisor

        return MindSupervisor
    aliases = {
        "llm_client": "mind.llm.client",
        "llm_memory": "mind.llm.memory",
        "llama_server_process": "mind.llm.process",
        "llm_to_tts": "mind.communication.llm_to_tts",
    }
    if name in aliases:
        import importlib

        return importlib.import_module(aliases[name])
    raise AttributeError(f"module {__name__} has no attribute {name}")
