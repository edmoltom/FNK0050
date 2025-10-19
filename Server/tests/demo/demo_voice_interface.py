"""Test script to run the full voice interface (STT -> LLM -> TTS)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SERVER_ROOT = PROJECT_ROOT / "Server"

for path in (PROJECT_ROOT, SERVER_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from Server.interface.VoiceInterface import ConversationManager


def main(prompt: str = None) -> None:
    """
    Entry point for run.py
    """
    print("[INFO] Starting ConversationManager… (Ctrl+C to stop)")
    ConversationManager().run()


if __name__ == "__main__":
    main()
