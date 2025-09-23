from __future__ import annotations

import sys
import threading
import types
from pathlib import Path

import pytest
from urllib import error as urllib_error

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

core_stub = types.ModuleType("core")
core_stub.__path__ = [str(SERVER_ROOT / "core")]
sys.modules.setdefault("core", core_stub)

requests_stub = types.ModuleType("requests")


def _fail_post(*_args, **_kwargs):  # pragma: no cover - guardrail
    raise AssertionError("Unexpected HTTP call during tests")


requests_stub.post = _fail_post
sys.modules.setdefault("requests", requests_stub)

from core.llm.llm_client import LlamaClient
from core.llm.llama_server_process import LlamaServerProcess
from app.services.conversation_service import ConversationService


class DummyResponse:
    def __init__(self, status_code: int) -> None:
        self.status = status_code

    def __enter__(self) -> "DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_conversation_service_waits_for_health(
    monkeypatch: pytest.MonkeyPatch, dummy_binary: Path, dummy_model: Path
) -> None:
    attempts: list[int] = []

    def fake_urlopen(req, timeout: float | None = None) -> DummyResponse:
        attempts.append(1)
        if len(attempts) < 3:
            raise urllib_error.URLError("not ready yet")
        return DummyResponse(200)

    monkeypatch.setattr("core.llm.llama_server_process.urllib_request.urlopen", fake_urlopen)

    process = LlamaServerProcess(
        llama_binary=dummy_binary,
        model_path=dummy_model,
        port=18180,
        extra_args=["--ready-after", "0.1"],
    )
    client = LlamaClient(base_url="http://dummy")

    service = ConversationService(
        process=process,
        client=client,
        health_timeout=1.5,
        health_check_interval=0.05,
        health_check_max_retries=1,
        health_check_backoff=1.0,
    )

    not_ready_called = threading.Event()
    service.add_not_ready_callback(lambda: not_ready_called.set())

    service.start()
    try:
        assert service.wait_for_ready(timeout=5.0)
    finally:
        service.stop()

    assert len(attempts) >= 3
    assert not_ready_called.is_set()


def test_watchdog_reports_exit(
    monkeypatch: pytest.MonkeyPatch, dummy_binary: Path, dummy_model: Path
) -> None:
    def fake_urlopen(req, timeout: float | None = None) -> DummyResponse:
        return DummyResponse(200)

    monkeypatch.setattr("core.llm.llama_server_process.urllib_request.urlopen", fake_urlopen)

    process = LlamaServerProcess(
        llama_binary=dummy_binary,
        model_path=dummy_model,
        port=18181,
        extra_args=["--ready-after", "0.1", "--exit-after", "0.3"],
    )
    client = LlamaClient(base_url="http://dummy")

    service = ConversationService(
        process=process,
        client=client,
        health_timeout=2.0,
        health_check_interval=0.05,
        health_check_max_retries=1,
    )

    exit_event = threading.Event()

    def _on_exit(_code: int | None) -> None:
        exit_event.set()

    service.add_exit_callback(_on_exit)

    service.start()
    try:
        assert exit_event.wait(timeout=5.0)
    finally:
        service.stop()
