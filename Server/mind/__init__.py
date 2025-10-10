"""
The 'mind' package contains Lumo's cognitive and language modules.
It includes the LLM interface, memory systems, persona, and reasoning bridge.
"""

from typing import TYPE_CHECKING

__all__ = ["MindContext", "initialize_mind"]

if TYPE_CHECKING:  # pragma: no cover
    from .context import MindContext as _MindContext


def initialize_mind(config):
    """Create and initialize the unified MindContext."""
    from .context import MindContext

    return MindContext(config)


def __getattr__(name):
    if name == "MindContext":
        from .context import MindContext

        return MindContext
    raise AttributeError(f"module 'mind' has no attribute {name!r}")
