"""
Test script to run the full voice interface (STT -> LLM -> TTS).
"""

import sys
from pathlib import Path

# Make sure the core folder is on the import path
sys.path.append(str(Path(__file__).resolve().parents[1] / "core"))

from Voice_interface import ConversationManager


def main(prompt: str = None) -> None:
    """
    Entry point for run.py
    """
    print("[INFO] Starting ConversationManager… (Ctrl+C to stop)")
    ConversationManager().run()


if __name__ == "__main__":
    main()