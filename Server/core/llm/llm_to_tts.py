from __future__ import annotations

import argparse
import sys
from pathlib import Path

from persona import build_system
from llm_client import LlamaClient
from core.voice.tts import TextToSpeech

THIS_DIR = Path(__file__).resolve().parent
# Reuse the TTS engine as a library instead of spawning a subprocess
_tts = TextToSpeech()

# Limit LLM verbosity so TTS flows better
MAX_REPLY_CHARS = 220

# --- TTS ----------------------------------------------------------------------
def speak_text(text: str):
    """Send text to the TTS engine and play audio."""
    try:
        _tts.speak(text)
    except Exception as e:  # pragma: no cover - runtime errors only
        print(f"[ERROR] TTS failed: {e}")

# --- CLI ----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query the local LLM and speak the reply.")
    parser.add_argument("prompt", help="Texto a enviar al modelo")
    parser.add_argument(
        "--base-url",
        dest="base_url",
        default=None,
        help="URL base del servidor LLaMA (por defecto usa LLAMA_BASE o http://127.0.0.1:8080)",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=float,
        default=None,
        help="Timeout de la petición en segundos (por defecto 30)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = LlamaClient(base_url=args.base_url, request_timeout=args.timeout)
    system = build_system()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": args.prompt},
    ]
    reply = client.query(messages, max_reply_chars=MAX_REPLY_CHARS)
    if not reply:
        print("[WARN] No reply from LLM.")
        return

    print(f"[LLM] {reply}")
    speak_text(reply)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Execution interrupted by user (Ctrl+C).")
