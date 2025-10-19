from __future__ import annotations

import sys
import types

import pytest

requests_stub = types.ModuleType("requests")


def _fail_post(*_args, **_kwargs):  # pragma: no cover - guardrail
    raise AssertionError("Unexpected HTTP call during tests")


requests_stub.post = _fail_post
sys.modules["requests"] = requests_stub

from Server.mind.llm.client import CHAT_ENDPOINT, LlamaClient


def test_llama_client_uses_env_base_when_not_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLAMA_BASE", "http://env.example:8080/")

    client = LlamaClient()

    assert client.base_url == "http://env.example:8080"
    assert client.chat_url == f"http://env.example:8080{CHAT_ENDPOINT}"


def test_llama_client_prefers_explicit_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLAMA_BASE", "http://env.example:8080")

    client = LlamaClient(base_url="http://override.local:9000/")

    assert client.base_url == "http://override.local:9000"
    assert client.chat_url == f"http://override.local:9000{CHAT_ENDPOINT}"


def test_llama_client_query_uses_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLAMA_BASE", raising=False)

    class DummyHTTP:
        def __init__(self) -> None:
            self.calls: list[tuple[str, float, dict]] = []

        def post(self, url: str, json: dict, timeout: float):
            self.calls.append((url, timeout, json))

            class _Resp:
                @staticmethod
                def raise_for_status() -> None:
                    return None

                @staticmethod
                def json() -> dict:
                    return {"choices": [{"message": {"content": "hola"}}]}

            return _Resp()

    dummy_http = DummyHTTP()
    client = LlamaClient(base_url="http://explicit.host", request_timeout=12.5, http_client=dummy_http)

    reply = client.query([{"role": "user", "content": "hola"}], max_reply_chars=100)

    assert reply == "hola"
    assert dummy_http.calls[0][0] == f"http://explicit.host{CHAT_ENDPOINT}"
    assert dummy_http.calls[0][1] == 12.5
