import sys
import subprocess
from pathlib import Path
import argparse
from persona import build_system
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
    system = build_system()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": args.prompt},
    ]
    reply = query_llm(messages, max_reply_chars=MAX_REPLY_CHARS)
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
