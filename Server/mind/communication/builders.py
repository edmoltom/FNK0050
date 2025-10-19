"""
Communication builders for Lumo's conversation stack.
Creates a consistent set of components shared by voice and CLI interfaces.
"""

from __future__ import annotations

import logging

from mind.persona import build_system
from mind.llm.client import LlamaClient
from mind.llm.memory import ConversationMemory
from mind.llm.settings import DEFAULT_TIMEOUT
from core.voice.tts import TextToSpeech

logger = logging.getLogger(__name__)


def build_conversation_stack(base_url: str | None = None, timeout: float = DEFAULT_TIMEOUT):
    """
    Build and wire a conversation-ready stack:
    - Persona policy
    - ConversationMemory
    - LlamaClient (configured for the persona)
    - TextToSpeech

    Returns (client, memory, tts, persona)
    """
    persona = build_system()
    memory = ConversationMemory()
    client = LlamaClient(base_url=base_url, request_timeout=timeout)
    tts = TextToSpeech()
    logger.info("[COMM] Conversation stack built successfully.")
    return client, memory, tts, persona
