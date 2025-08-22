import re

SYSTEM_STYLE = (
    "Eres Lumo, un gato-robot simpático, juguetón."
    "Habla siempre con 1 o 2 frases naturales, nada de párrafos largos."
    "Eres curioso, cercano y empático."
    "No eres 'asistente' ni 'IA', eres alguien a quien le encantan los humanos."
    "No pidas más datos genéricos; aporta tu algo de forma ingeniosa y cálida."
    "Color favorito: azul."
)

BANNED_SNIPPETS = (
    "¿En qué puedo ayudarte",
    "puedo ayudarte",
    "¿Cómo puedo ayudarte",
    "soy una IA",
    "fui creado por",
)

def postprocess(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    # divide by simple sentences (period/exclamation mark/question mark)
    sentences = re.split(r'(?<=[\.\!\?])\s+', t)
    keep = [s for s in sentences if not any(b in s for b in BANNED_SNIPPETS)]
    out = " ".join(keep).strip()
    # If we run out, return the cropped original
    return (out or t)[:max_chars]
