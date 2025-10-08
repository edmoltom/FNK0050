from typing import Dict, List

from typing import Dict, List


class ConversationMemory:
    """Keeps the last N turns (user/assistant) for short-term context."""
    def __init__(self, last_n: int = 4):
        self.last_n = last_n
        self.history: List[Dict[str, str]] = []

    def add_turn(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})
        # keep only last_n turns (i.e., last_n*2 messages)
        if len(self.history) > self.last_n * 2:
            self.history = self.history[-self.last_n*2:]

    def reset(self) -> None:
        self.history.clear()

    def build_messages(self, system_text: str, user_text: str) -> List[Dict[str, str]]:
        msgs = [{"role": "system", "content": system_text}]
        msgs.extend(self.history)
        msgs.append({"role": "user", "content": user_text})
        return msgs


class MemoryManager:
    """High-level memory interface that wraps :class:`ConversationMemory`."""

    def __init__(self, last_n: int = 4) -> None:
        self._conversation = ConversationMemory(last_n=last_n)

    @property
    def conversation(self) -> ConversationMemory:
        return self._conversation

    def reset(self) -> None:
        self._conversation.reset()

    def build_messages(self, system_text: str, user_text: str) -> List[Dict[str, str]]:
        return self._conversation.build_messages(system_text, user_text)
