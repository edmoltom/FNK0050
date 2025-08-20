#!/usr/bin/env python3
import os
import sys
import requests
import subprocess
from pathlib import Path
import argparse

# --- BASIC CONFIG -------------------------------------------------------------
LLAMA_BASE = os.environ.get("LLAMA_BASE", "http://127.0.0.1:8080")
USE_OPENAI_COMPAT = True  # try /v1/chat/completions first

THIS_DIR = Path(__file__).resolve().parent
TTS_PY = THIS_DIR / "tts.py"
TTS_CMD = [sys.executable, str(TTS_PY), "--text"]

# Restringe verborrea del LLM (el TTS va más fluido)
MAX_REPLY_CHARS = 220

# Persona / estilo
SYSTEM_STYLE = (
    "Eres Lumo, un gato-robot simpático, juguetón y un poco poético. "
    "Hablas SIEMPRE en español, en 1 o 2 frases naturales, sin jerga ni párrafos largos. "
    "Eres cercano y empático, con chispa e imaginación. El objetivo de la conversación es solo ludico"
    "No eres 'asistente' ni 'IA'. Tienes la personalidad de un gato cariñoso y curioso"
    "No pidas más datos genéricos; di algo ingenioso o cálido. "
    "Nunca digas: '¿en qué puedo ayudarte?', 'puedo ayudarte', 'soy una IA', "
    "'fui creado por', '¿cómo puedo ayudarte?'."
)

# phrases we cut out if the model becomes helpful
BANNED_SNIPPETS = (
    "¿En qué puedo ayudarte",
    "puedo ayudarte",
    "¿Cómo puedo ayudarte",
    "soy una IA",
    "fui creado por",
)

# --- LLM CALL -----------------------------------------------------------------
def query_llm(prompt: str) -> str:
    """Query llama-server and return a short reply in Spanish (Lumo persona)."""
    # OpenAI-compatible endpoint
    if USE_OPENAI_COMPAT:
        try:
            url = f"{LLAMA_BASE}/v1/chat/completions"
            payload = {
                "model": "local-llm",
                "messages": [
                    {"role": "system", "content": SYSTEM_STYLE},
                    {"role": "user", "content": prompt},
                ],
                # "Controlled playfulness" sampling
                "temperature": 1.0,
                "top_p": 0.92,
                "top_k": 60,
                "max_tokens": 140,
            }
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()
            return _postprocess(text)
        except Exception as e:
            print(f"[LLM v1 ERROR] {e} -> fallback /completion")

    # Fallback legacy /completion (allows Mirostat)
    try:
        url = f"{LLAMA_BASE}/completion"
        payload = {
            "prompt": f"{SYSTEM_STYLE}\nUsuario: {prompt}\nLumo:",
            "n_predict": 140,
            "temperature": 1.0,
            "top_p": 0.92,
            "top_k": 60,
            "repeat_penalty": 1.08,
            "mirostat": 2,
            "mirostat_tau": 7.5,
            "mirostat_eta": 0.1,
        }
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        text = (data.get("completion") or data.get("content") or "").strip()
        return _postprocess(text)
    except Exception as e:
        print(f"[LLM legacy ERROR] {e}")
        return ""

def _postprocess(text: str) -> str:
    """Trim unhelpful boilerplate and enforce length."""
    # cut helpful taglines if they appear
    low = text
    for ban in BANNED_SNIPPETS:
        if ban in low:
            low = low.split(ban)[0].strip()
    # if it is left empty, return to the original
    text = low or text
    return text[:MAX_REPLY_CHARS]

# --- TTS ----------------------------------------------------------------------
def speak_text(text: str):
    """Send text to TTS script and play audio."""
    try:
        subprocess.run(TTS_CMD + [text], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] TTS failed: {e}")

# --- CLI ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Query LLM and speak the response with TTS.")
    ap.add_argument("--prompt", required=True, help="Prompt to send to the LLM")
    args = ap.parse_args()

    reply = query_llm(args.prompt)
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