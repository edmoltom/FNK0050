"""Utility script to start llama-server with defaults (mind.scripts.start_llama_server)."""

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logger.info("[LLM] Module loaded: mind.scripts.start_llama_server")

HOME = Path.home()
SERVER = HOME / "llama.cpp/build/bin/llama-server"
MODEL = HOME / "llama.cpp/models/qwen2.5-0.5b-instruct-q3_k_m.gguf"

ARGS = [
    str(SERVER),
    "-m",
    str(MODEL),
    "--mlock",  # if enough RAM is available, prevents paging
    "-t",
    "3",
    "-c",
    "384",
    "--port",
    "8080",
]


def main() -> None:
    if not SERVER.exists():
        sys.exit(f"[ERROR] llama-server not found: {SERVER}")
    if not MODEL.exists():
        sys.exit(f"[ERROR] Model not found: {MODEL}")

    print("[INFO] Launching llama-server…")
    try:
        subprocess.run(ARGS, check=False)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user (Ctrl+C). Shutting down…")


if __name__ == "__main__":
    main()
