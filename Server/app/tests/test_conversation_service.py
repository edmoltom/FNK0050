from __future__ import annotations

import os
import sys
import threading
import types
from pathlib import Path
from typing import Any, Dict
from unittest import mock

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

core_stub = types.ModuleType("core")
core_stub.__path__ = []  # type: ignore[attr-defined]
sys.modules.setdefault("core", core_stub)

llm_stub = types.ModuleType("core.llm")
llm_stub.__path__ = []  # type: ignore[attr-defined]
sys.modules.setdefault("core.llm", llm_stub)

llama_stub = types.ModuleType("core.llm.llama_server_process")


class _StubLlamaServerProcess:  # pragma: no cover - test scaffolding
    pass


llama_stub.LlamaServerProcess = _StubLlamaServerProcess
sys.modules.setdefault("core.llm.llama_server_process", llama_stub)

llm_client_stub = types.ModuleType("core.llm.llm_client")


class _StubLlamaClient:  # pragma: no cover - test scaffolding
    def __init__(self, *, base_url: str | None = None, request_timeout: float | None = None) -> None:
        if base_url is None:
            base_url = os.getenv("LLAMA_BASE")
        self.base_url = base_url
        self.request_timeout = request_timeout


llm_client_stub.LlamaClient = _StubLlamaClient
sys.modules.setdefault("core.llm.llm_client", llm_client_stub)

from app.services.conversation_service import ConversationService


class ProcessMock:
    def __init__(self) -> None:
        self._running = False
        self.start = mock.Mock(side_effect=self._start)
        self.wait_ready = mock.Mock(return_value=True)
        self.terminate = mock.Mock(side_effect=self._terminate)
        self.is_running = mock.Mock(side_effect=self._is_running)

    def _start(self) -> None:
        self._running = True

    def _terminate(self, timeout: float = 5.0) -> None:  # pragma: no cover - signature parity
        self._running = False

    def _is_running(self) -> bool:
        return self._running


def _build_service(
    process: ProcessMock,
    *,
    manager_factory: mock.Mock,
    readiness_timeout: float = 0.1,
    shutdown_timeout: float = 0.1,
) -> ConversationService:
    dummy_dep = object()
    return ConversationService(
        stt=dummy_dep,
        tts=dummy_dep,
        led_controller=dummy_dep,
        llm_client=dummy_dep,
        process=process,  # type: ignore[arg-type]
        manager_factory=manager_factory,
        readiness_timeout=readiness_timeout,
        shutdown_timeout=shutdown_timeout,
    )


def _manager_factory_factory(events: Dict[str, threading.Event]) -> mock.Mock:
    created: list[mock.Mock] = []

    def _factory(**_kwargs: Any) -> mock.Mock:
        manager = mock.Mock()

        def _run(*, stop_event: threading.Event) -> None:
            events["run_started"].set()
            stop_event.wait()
            events["run_finished"].set()

        manager.run = mock.Mock(side_effect=_run)
        manager.pause_stt = mock.Mock()
        manager.drain_queues = mock.Mock()
        manager.request_stop = mock.Mock()
        manager.stop = mock.Mock()
        created.append(manager)
        return manager

    factory = mock.Mock(side_effect=_factory)
    factory.created = created  # type: ignore[attr-defined]
    return factory


def test_conversation_service_start_stop_multiple_times() -> None:
    process = ProcessMock()
    events = {
        "run_started": threading.Event(),
        "run_finished": threading.Event(),
    }
    manager_factory = _manager_factory_factory(events)

    service = _build_service(process, manager_factory=manager_factory)

    service.start()
    assert events["run_started"].wait(timeout=1.0)
    service.stop()
    assert events["run_finished"].wait(timeout=1.0)

    last_manager = manager_factory.created[-1]
    last_manager.pause_stt.assert_called_once()
    last_manager.drain_queues.assert_called_once()

    assert process.start.call_count == 1
    assert process.terminate.call_count >= 1
    assert service.join() is True

    # Reset events for the second cycle
    events["run_started"].clear()
    events["run_finished"].clear()

    service.start()
    assert events["run_started"].wait(timeout=1.0)
    service.stop()
    assert events["run_finished"].wait(timeout=1.0)
    assert service.join() is True

    assert len(manager_factory.created) == 2
    assert process.start.call_count == 2
    assert process.wait_ready.call_count == 2


def test_stop_is_idempotent_when_readiness_never_met(caplog: pytest.LogCaptureFixture) -> None:
    process = ProcessMock()
    process.wait_ready.return_value = False

    manager_factory = mock.Mock()
    service = _build_service(process, manager_factory=manager_factory)

    caplog.set_level("ERROR")
    service.start()

    assert any("Timeout waiting for llama server readiness" in record.message for record in caplog.records)
    manager_factory.assert_not_called()

    service.stop()
    service.stop()  # idempotent

    assert process.terminate.call_count >= 1
    assert service.join() is True

