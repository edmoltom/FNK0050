import os
import sys
import requests
import subprocess
import re
from pathlib import Path
import argparse

# --- BASIC CONFIGURATION ------------------------------------------------------
LLAMA_BASE = os.environ.get("LLAMA_BASE", "http://127.0.0.1:8080")
USE_OPENAI_COMPAT = True   # /v1/chat/completions if llama-server supports it

THIS_DIR = Path(__file__).resolve().parent
TTS_PY = THIS_DIR / "tts.py"  # absolute path to tts.py in the same directory
TTS_CMD = [sys.executable, str(TTS_PY), "--text"]

MAX_REPLY_CHARS = 280  # avoid overly long replies
SYSTEM_STYLE = (
    "You are the voice of a robot. "
    "Respond briefly in Spanish, suitable for Text-to-Speech. "
    "Avoid long paragraphs, be concise."
)
# ------------------------------------------------------------------------------


def query_llm(prompt: str) -> str:
    """Query the LLM server with a given prompt and return the reply text."""
    try:
        if USE_OPENAI_COMPAT:
            url = f"{LLAMA_BASE}/v1/chat/completions"
            payload = {
                "model": "local-llm",
                "messages": [
                    {"role": "system", "content": SYSTEM_STYLE},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 200,
            }
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            url = f"{LLAMA_BASE}/completion"
            payload = {
                "prompt": f"{SYSTEM_STYLE}\nUser: {prompt}\nAssistant:",
                "n_predict": 200,
                "temperature": 0.7,
            }
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data.get("content", "").strip()
    except Exception as e:
        print(f"[ERROR] LLM query failed: {e}")
        return ""


def speak_text(text: str):
    """Send text to TTS script and play audio."""
    try:
        subprocess.run(TTS_CMD + [text], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] TTS failed: {e}")


def chunk_sentences(text: str):
    """Split text into smaller sentences for lower latency TTS playback."""
    return re.findall(r'([^.!?]+[.!?])', text)


def main():
    parser = argparse.ArgumentParser(description="Query LLM and speak the response with TTS.")
    parser.add_argument("--prompt", required=True, help="Prompt to send to the LLM")
    args = parser.parse_args()

    reply = query_llm(args.prompt)
    if not reply:
        print("[WARN] No reply from LLM.")
        return

    reply = reply[:MAX_REPLY_CHARS]
    print(f"[LLM] {reply}")

    # Split into sentences to reduce perceived latency
    for sentence in chunk_sentences(reply):
        speak_text(sentence.strip())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Execution interrupted by user (Ctrl+C).")
