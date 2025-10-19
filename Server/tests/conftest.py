from __future__ import annotations

import importlib
import stat
import sys
from pathlib import Path

import pytest


SERVER_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = SERVER_ROOT.parent

for path in (PROJECT_ROOT, SERVER_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

sys.modules.setdefault("app", importlib.import_module("Server.app"))
sys.modules.setdefault("core", importlib.import_module("Server.core"))
sys.modules.setdefault("interface", importlib.import_module("Server.interface"))
sys.modules.setdefault("mind", importlib.import_module("Server.mind"))


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
parser.add_argument('--exit-after', type=float, default=0.0)
args, _ = parser.parse_known_args()

print('Dummy llama-server starting', flush=True)
if args.ready_after:
    time.sleep(args.ready_after)
print('HTTP server listening on port', args.port, flush=True)

exit_deadline = None
if args.exit_after:
    exit_deadline = time.monotonic() + args.exit_after

try:
    while True:
        time.sleep(0.1)
        if exit_deadline is not None and time.monotonic() >= exit_deadline:
            print('Dummy llama-server exiting', flush=True)
            sys.exit(0)
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
