# hearing/text_norm.py
import re

_Q = r"(que|qué|cual|cuál|como|cómo|donde|dónde|cuando|cuándo|por que|por qué|cuanto|cuánto|quien|quién|cuáles|cuantos|cuántos)"

def normalize_punct(s: str) -> str:
    t = (s or "").strip()
    if not t:
        return t
    # ¿Es pregunta?
    is_q = t.endswith("?") or re.search(rf"\b{_Q}\b", t.lower()) is not None
    # Limpia ? sobrantes al final
    t = re.sub(r"\?+$", "", t).strip()
    if is_q:
        # Añade signo de apertura si no lo tiene
        if not t.startswith("¿"):
            t = "¿" + t
        t = t + "?"
    else:
        # Asegura un cierre . ! ?
        if not re.search(r"[\.!\?]$", t):
            t = t + "."
    return t
