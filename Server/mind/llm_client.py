"""HTTP client to interact with the local LLaMA REST API."""

from __future__ import annotations

import os
from typing import Iterable, MutableMapping, Optional, Sequence

import requests

from .persona import MAX_TOKENS, TEMP, TOP_K, TOP_P, postprocess

DEFAULT_BASE_URL = "http://127.0.0.1:8080"
CHAT_ENDPOINT = "/v1/chat/completions"


class LlamaClient:
    """Small HTTP client specialised for the llama.cpp compatible API."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        request_timeout: Optional[float] = None,
        model: str = "local-llm",
        http_client: Optional[object] = None,
        stop_sequences: Optional[Sequence[str]] = None,
    ) -> None:
        env_base = os.getenv("LLAMA_BASE", DEFAULT_BASE_URL)
        chosen_base = base_url or env_base
        self.base_url = chosen_base.rstrip("/") or DEFAULT_BASE_URL
        self.request_timeout = 30.0 if request_timeout is None else float(request_timeout)
        self.model = model
        self._http = http_client or requests
        self.stop_sequences: Sequence[str] = (
            stop_sequences if stop_sequences is not None else ["\n", "Usuario:", "Lumo:"]
        )

    @property
    def chat_url(self) -> str:
        """Return the absolute URL used for chat completions."""

        return f"{self.base_url}{CHAT_ENDPOINT}"

    def build_payload(self, messages: Iterable[MutableMapping[str, str]]) -> MutableMapping[str, object]:
        """Assemble the JSON payload for the llama.cpp REST endpoint."""

        return {
            "model": self.model,
            "messages": list(messages),
            "temperature": TEMP,
            "top_p": TOP_P,
            "top_k": TOP_K,
            "max_tokens": MAX_TOKENS,
            "repetition_penalty": 1.15,
            "no_repeat_ngram_size": 3,
            "stop": list(self.stop_sequences),
        }

    def query(self, messages: Sequence[MutableMapping[str, str]], *, max_reply_chars: int = 220) -> str:
        """Execute a chat completion request and post-process the answer."""

        payload = self.build_payload(messages)
        response = self._http.post(self.chat_url, json=payload, timeout=self.request_timeout)
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        return postprocess(text, max_reply_chars)


def build_default_client() -> LlamaClient:
    """Create a :class:`LlamaClient` instance using defaults and env fallbacks."""

    return LlamaClient()
