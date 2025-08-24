import os, requests
from .persona import postprocess, TEMP, TOP_P, TOP_K, MAX_TOKENS

LLAMA_BASE = os.getenv("LLAMA_BASE", "http://127.0.0.1:8080")

def query_llm(messages, max_reply_chars: int = 220) -> str:
    url = f"{LLAMA_BASE}/v1/chat/completions"
    payload = {
        "model": "local-llm",
        "messages": messages,
        "temperature": TEMP,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "max_tokens": MAX_TOKENS,
        "repetition_penalty": 1.15,
        "no_repeat_ngram_size": 3,
        "stop": ["\n", "Usuario:", "Lumo:"],
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    return postprocess(text, max_reply_chars)
