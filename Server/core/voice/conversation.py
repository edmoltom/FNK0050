from __future__ import annotations

"""Conversation state management for the voice interface."""

from abc import ABC, abstractmethod
from typing import List, Sequence, Optional

from core.llm.llm_memory import ConversationMemory
from core.llm.persona import build_system


class LLMInterface(ABC):
    """Abstract large language model client."""

    @abstractmethod
    def ask(self, messages: List[dict]) -> str:
        """Return a reply given a conversation ``messages`` history."""


class DefaultLLM(LLMInterface):
    """Use the repository's shared LLM client."""

    def ask(self, messages: List[dict]) -> str:  # pragma: no cover - thin wrapper
        from core.llm.llm_client import query_llm

        return query_llm(messages, max_reply_chars=220)


class ConversationManager:
    """Keeps track of wake words and conversational memory."""

    def __init__(
        self,
        llm: LLMInterface,
        wake_words: Sequence[str],
        memory: Optional[ConversationMemory] = None,
    ) -> None:
        self.llm = llm
        self.wake_words = [w.lower() for w in wake_words]
        self.memory = memory or ConversationMemory(last_n=3)

    def contains_wake_word(self, text: str) -> bool:
        t = text.lower()
        return any(w in t for w in self.wake_words)

    def process(self, text: str) -> Optional[str]:
        """Process a transcribed ``text`` and maybe return a reply."""
        if not self.contains_wake_word(text):
            return None
        msgs = self.memory.build_messages(build_system(), text)
        reply = self.llm.ask(msgs)
        self.memory.add_turn(text, reply)
        return reply
