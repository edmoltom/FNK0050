from __future__ import annotations

"""Conversation state management for the voice interface."""

from typing import Sequence, Optional

from core.llm.base import LLMClient
from core.llm.llm_memory import ConversationMemory
from core.llm.persona import build_system


class ConversationManager:
    """Keeps track of wake words and conversational memory."""

    def __init__(
        self,
        llm: LLMClient,
        wake_words: Sequence[str],
        memory: Optional[ConversationMemory] = None,
        max_reply_chars: int = 220,
    ) -> None:
        self.llm = llm
        self.wake_words = [w.lower() for w in wake_words]
        self.memory = memory or ConversationMemory(last_n=3)
        self.max_reply_chars = max_reply_chars

    def contains_wake_word(self, text: str) -> bool:
        t = text.lower()
        return any(w in t for w in self.wake_words)

    def process(self, text: str) -> Optional[str]:
        """Process a transcribed ``text`` and maybe return a reply."""
        if not self.contains_wake_word(text):
            return None
        msgs = self.memory.build_messages(build_system(), text)
        reply = self.llm.query(msgs, self.max_reply_chars)
        self.memory.add_turn(text, reply)
        return reply
