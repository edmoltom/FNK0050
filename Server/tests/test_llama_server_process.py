from __future__ import annotations

import stat
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


@pytest.fixture()
def dummy_binary(tmp_path: Path) -> Path:
    script = tmp_path / "dummy_llama_server.py"
    script.write_text(
        """#!/usr/bin/env python3
import argparse
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('-m')
parser.add_argument('--port')
parser.add_argument('-t')
parser.add_argument('--parallel')
parser.add_argument('-c')
parser.add_argument('-b')
parser.add_argument('--mlock', action='store_true')
parser.add_argument('--embeddings', action='store_true')
parser.add_argument('--ready-after', type=float, default=0.0)
args, _ = parser.parse_known_args()

print('Dummy llama-server starting', flush=True)
if args.ready_after:
    time.sleep(args.ready_after)
print('HTTP server listening on port', args.port, flush=True)

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    sys.exit(0)
"""
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


@pytest.fixture()
def dummy_model(tmp_path: Path) -> Path:
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    return model


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
