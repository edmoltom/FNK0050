"""
Start llama-server (Qwen 0.5B) with sane defaults for Raspberry Pi.

Note: persona and sampling are controlled in the client (llm_to_tts.py),
not here.
"""
import subprocess
from pathlib import Path
import sys

HOME   = Path.home()
SERVER = HOME / "llama.cpp/build/bin/llama-server"
MODEL  = HOME / "llama.cpp/models/qwen2.5-0.5b-instruct-q3_k_m.gguf"

ARGS = [
    str(SERVER),
    "-m", str(MODEL),
    "--mlock",            # if enough RAM is available, prevents paging
    "-t", "3",            # CPU threads; raise to 3 if the Pi can handle it
    "-c", "160",          # short context for lighter usage
    "--port", "8080",     # HTTP port
]

def main():
    if not SERVER.exists():
        sys.exit(f"[ERROR] llama-server not found: {SERVER}")
    if not MODEL.exists():
        sys.exit(f"[ERROR] Model not found: {MODEL}")

    print("[INFO] Launching llama-server…")
    try:
        subprocess.run(ARGS, check=False)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user (Ctrl+C). Shutting down…")

if __name__ == "__main__":
    main()
