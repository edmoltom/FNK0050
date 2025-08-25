# ---------------------------------------------------------------------------
# test_voice_loop.py — Orchestrated test: STT → LLM → TTS
# ---------------------------------------------------------------------------
# Launches your STT script as a subprocess (unbuffered) and reads lines.
# Whenever a line starts with "> ", it is considered a full utterance and
# is sent to the LLM→TTS bridge (llm_to_tts.py).
#
# Usage (from your project root):
#   python3 run.py --test voice_loop
#
from pathlib import Path as _Path
import subprocess as _subprocess, sys as _sys, os as _os, argparse as _argparse

# --- Paths (adjust if needed) ---
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
_LLM_TO_TTS = _PROJECT_ROOT / "core" / "llm" / "llm_to_tts.py"
# Updated path to the speech-to-text helper in the hearing module
_STT_SCRIPT = _PROJECT_ROOT / "core" / "hearing" / "stt.py"

def main():  # entrypoint expected by your run.py
    ap = _argparse.ArgumentParser(add_help=False)
    ap.add_argument("--llama", default=_os.environ.get("LLAMA_BASE", "http://127.0.0.1:8080"))
    args, _ = ap.parse_known_args()

    if not _LLM_TO_TTS.exists():
        print(f"[ERROR] Not found: {_LLM_TO_TTS}"); return False
    if not _STT_SCRIPT.exists():
        print(f"[ERROR] Not found: {_STT_SCRIPT}"); return False

    env = _os.environ.copy()
    env["LLAMA_BASE"] = args.llama

    print("[INFO] Starting STT… (Ctrl+C to stop)")
    stt = _subprocess.Popen([_sys.executable, "-u", str(_STT_SCRIPT)],
                            stdout=_subprocess.PIPE, stderr=_subprocess.STDOUT,
                            text=True, bufsize=1, env=env)

    try:
        for line in stt.stdout:
            line = line.rstrip()
            print(line)
            # Full utterances from STT are printed as lines starting with "> "
            if line.startswith("> "):
                utterance = line[2:].strip()
                if utterance:
                    # Send to LLM → TTS bridge
                    _subprocess.run([_sys.executable, str(_LLM_TO_TTS),
                                     "--prompt", utterance],
                                    check=False, env=env)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user (Ctrl+C). Stopping…")
    finally:
        try:
            stt.terminate(); stt.wait(timeout=3)
        except Exception:
            stt.kill()
    return True

if __name__ == "__main__":
    main()
