# llm_client.py
import os
import requests
from persona import SYSTEM_STYLE, postprocess

LLAMA_BASE = os.getenv("LLAMA_BASE", "http://127.0.0.1:8080")

def query_llm(prompt: str, max_reply_chars: int = 220) -> str:
    """Query llama-server via /v1/chat/completions and return a short reply."""
    url = f"{LLAMA_BASE}/v1/chat/completions"
    payload = {
        "model": "local-llm",
        "messages": [
            {"role": "system", "content": SYSTEM_STYLE},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.85,
        "top_p": 0.9,
        "top_k": 50,
        "max_tokens": 75,
        "stop": ["\n", "Usuario:", "Lumo:"],
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
        return postprocess(text, max_reply_chars)
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return ""