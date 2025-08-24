from __future__ import annotations

"""Core interfaces for large language model clients."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMClient(ABC):
    """Interface for querying language models."""

    @abstractmethod
    def query(self, messages: List[Dict[str, Any]], max_chars: int) -> str:
        """Return a response for ``messages`` limited to ``max_chars``."""
        raise NotImplementedError
