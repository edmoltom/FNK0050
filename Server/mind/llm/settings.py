"""Shared constants and defaults for Lumo's LLM subsystems."""

import logging

logger = logging.getLogger(__name__)
logger.info("[LLM] Module loaded: mind.llm.settings")

DEFAULT_STOP_SEQUENCES = ["###", "</s>"]
MAX_REPLY_CHARS = 500
HISTORY_TURNS = 6
DEFAULT_TIMEOUT = 30.0
