import sys
import time
from pathlib import Path
from unittest import mock

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from mind.llama_server_process import LlamaServerProcess
import mind.llama_server_process as llama_process_module


def test_start_is_non_blocking(dummy_binary: Path, dummy_model: Path) -> None:
    process = LlamaServerProcess(
        llama_binary=dummy_binary,
        model_path=dummy_model,
        port=18080,
        extra_args=["--ready-after", "0.1"],
    )

    start = time.perf_counter()
    process.start()
    elapsed = time.perf_counter() - start

    assert elapsed < 0.2
    process.terminate()


def test_wait_ready_respects_timeout(dummy_binary: Path, dummy_model: Path) -> None:
    process = LlamaServerProcess(
        llama_binary=dummy_binary,
        model_path=dummy_model,
        port=18081,
        extra_args=["--ready-after", "1.0"],
    )

    process.start()
    ready = process.wait_ready(timeout=0.1)

    assert not ready
    process.terminate()


def test_terminate_cleans_up_process(dummy_binary: Path, dummy_model: Path) -> None:
    process = LlamaServerProcess(
        llama_binary=dummy_binary,
        model_path=dummy_model,
        port=18082,
        extra_args=["--ready-after", "0.1"],
    )

    process.start()
    assert process.wait_ready(timeout=2.0)

    process.terminate()

    with pytest.raises(RuntimeError):
        process.wait_ready(timeout=0.1)


def test_poll_health_logs_backoff(
    dummy_binary: Path,
    dummy_model: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = LlamaServerProcess(
        llama_binary=dummy_binary,
        model_path=dummy_model,
        port=18083,
        ready_text=None,
    )

    mock_process = mock.Mock()
    mock_process.poll.return_value = None
    process._process = mock_process  # type: ignore[attr-defined]

    caplog.set_level("INFO")

    monkeypatch.setattr(
        "mind.llama_server_process.urllib_request.urlopen",
        mock.Mock(side_effect=llama_process_module.urllib_error.URLError("boom")),
    )

    fake_time = {"value": 0.0}

    def fake_monotonic() -> float:
        fake_time["value"] += 0.05
        return fake_time["value"]

    monkeypatch.setattr(llama_process_module.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(llama_process_module.time, "sleep", lambda _x: None)

    result = process.poll_health(
        "http://localhost:18083",
        timeout=0.5,
        interval=0.05,
        max_retries=1,
        backoff=2.0,
    )

    assert result is False

    llama_logs = [
        record.message for record in caplog.records if record.name == "conversation.llama"
    ]

    assert any("Health check request failed" in msg for msg in llama_logs)
    assert any("Health check backoff" in msg for msg in llama_logs)
    assert any("Health check failed after" in msg for msg in llama_logs)
