import sys
import time
import types
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

core_stub = types.ModuleType("core")
core_stub.__path__ = [str(SERVER_ROOT / "core")]
sys.modules.setdefault("core", core_stub)

from core.llm.llama_server_process import LlamaServerProcess


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
