"""
The 'mind' package contains Lumo's cognitive and language modules.
It includes the LLM interface, memory systems, persona, and reasoning bridge.
"""

from .context import MindContext


def initialize_mind(config):
    """Create and initialize the unified MindContext."""
    return MindContext(config)


__all__ = ["MindContext", "initialize_mind"]
