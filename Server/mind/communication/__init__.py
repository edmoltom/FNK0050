"""Communication helpers connecting the LLM to downstream systems."""

from .llm_to_tts import main as llm_to_tts_main

__all__ = ["llm_to_tts_main"]
