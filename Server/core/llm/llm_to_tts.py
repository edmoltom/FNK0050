#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
import argparse
from llm_client import query_llm

THIS_DIR = Path(__file__).resolve().parent
TTS_PY = THIS_DIR / "tts.py"
TTS_CMD = [sys.executable, str(TTS_PY), "--text"]

# Limit LLM verbosity so TTS flows better
MAX_REPLY_CHARS = 220

# --- TTS ----------------------------------------------------------------------
def speak_text(text: str):
    """Send text to TTS script and play audio."""
    try:
        subprocess.run(TTS_CMD + [text], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] TTS failed: {e}")

# --- CLI ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Query LLM and speak the response with TTS."
    )
    ap.add_argument("--prompt", required=True, help="Prompt to send to the LLM")
    args = ap.parse_args()

    reply = query_llm(args.prompt, max_reply_chars=MAX_REPLY_CHARS)
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
