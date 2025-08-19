from pathlib import Path
import subprocess, sys, os, argparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]     # /home/user/FNK0050

CANDIDATES = [
    PROJECT_ROOT / "Server" / "core" / "llm" / "llm_to_tts.py",
    PROJECT_ROOT / "core"   / "llm" / "llm_to_tts.py",
]
for c in CANDIDATES:
    if c.exists():
        LLM_TO_TTS = c
        break
else:
    LLM_TO_TTS = CANDIDATES[-1]  

def _execute(prompt: str) -> bool:
    env = os.environ.copy()
    env.setdefault("LLAMA_BASE", "http://127.0.0.1:8080")
    print(f"[INFO] Usando: {LLM_TO_TTS}")
    try:
        if not LLM_TO_TTS.exists():
            print(f"[ERROR] No encuentro: {LLM_TO_TTS}")
            return False
        subprocess.run([sys.executable, str(LLM_TO_TTS), "--prompt", prompt],
                       check=True, env=env)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Llamada falló: {e}")
        return False
    except KeyboardInterrupt:
        print("\n[INFO] Test interrumpido (Ctrl+C).")
        return False

def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--prompt", default="Di hola en una frase.")
    args, _ = ap.parse_known_args()
    ok = _execute(args.prompt)
    print("[OK]" if ok else "[FAIL]")

if __name__ == "__main__":
    main()