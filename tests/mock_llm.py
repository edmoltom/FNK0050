from Server.core.llm.base import LLMClient


class MockClient(LLMClient):
    """Simple in-memory LLM client for tests."""

    def __init__(self, prefix: str = "ACK: ") -> None:
        self.prefix = prefix
        self.queries = []

    def query(self, messages, max_chars):
        self.queries.append((messages, max_chars))
        return self.prefix + messages[-1]["content"][:max_chars]
