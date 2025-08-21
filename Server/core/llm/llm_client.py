# llm_client.py
import os
import requests
from persona import SYSTEM_STYLE, postprocess

LLAMA_BASE = os.getenv("LLAMA_BASE", "http://127.0.0.1:8080")

def query_llm(
    prompt: str, max_reply_chars: int = 220, endpoint_hint: str | None = None
) -> str:
    """
    Query a local llama.cpp server. Prefer the OpenAI-compatible endpoint;
    fallback to legacy /completion if needed. Always Spanish, brief, and post-filtered.
    """
    # Try OpenAI-compatible /v1/chat/completions
    try:
        if endpoint_hint in (None, "/v1/chat/completions"):
            url = f"{LLAMA_BASE}/v1/chat/completions"
            payload = {
                "model": "local-llm",
                "messages": [
                    {"role": "system", "content": SYSTEM_STYLE},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 1.0,
                "top_p": 0.92,
                "top_k": 60,
                "max_tokens": 140,
            }
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()
            return postprocess(text, max_reply_chars)
    except Exception:
        endpoint_hint = "/completion"

    # Fallback legacy /completion (allows Mirostat)
    url = f"{LLAMA_BASE}/completion"
    payload = {
        "prompt": f"{SYSTEM_STYLE}\nUsuario: {prompt}\nLumo:",
        "n_predict": 160,
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
    return postprocess(text, max_reply_chars)
