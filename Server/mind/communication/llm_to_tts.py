"""CLI bridge from LLM responses to TTS playback (mind.communication.llm_to_tts)."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from mind.communication.builders import build_conversation_stack
from ..llm.settings import MAX_REPLY_CHARS

logger = logging.getLogger(__name__)
logger.info("[LLM] Module loaded: mind.communication.llm_to_tts")

THIS_DIR = Path(__file__).resolve().parent


def speak_text(text: str, tts) -> None:
    """Send text to the TTS engine and play audio."""

    try:
        tts.speak(text)
    except Exception as exc:  # pragma: no cover - runtime errors only
        print(f"[ERROR] TTS failed: {exc}")


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
    if args.timeout is None:
        client, memory, tts, persona = build_conversation_stack(base_url=args.base_url)
    else:
        client, memory, tts, persona = build_conversation_stack(
            base_url=args.base_url, timeout=args.timeout
        )
    messages = memory.build_messages(persona, args.prompt)
    reply = client.query(messages, max_reply_chars=MAX_REPLY_CHARS)
    if not reply:
        print("[WARN] No reply from LLM.")
        return

    print(f"[LLM] {reply}")
    memory.add_turn(args.prompt, reply)
    speak_text(reply, tts)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Execution interrupted by user (Ctrl+C).")
