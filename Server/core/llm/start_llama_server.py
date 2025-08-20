"""
Start script for llama-server.

This wraps your compiled llama.cpp `llama-server` binary with the same
parameters you normally use with `llama-cli`, and exposes it as an HTTP server
for other modules (e.g. TTS or stimulus injection) to connect to.
"""

import subprocess
from pathlib import Path

# --- PATHS (adapt to your own environment) --------------------
HOME   = Path.home()
SERVER = HOME / "llama.cpp/build/bin/llama-server"
MODEL  = HOME / "llama.cpp/models/qwen2.5-0.5b-instruct-q3_k_m.gguf"

# --- PARAMETERS (same as your llama-cli run) ------------------
ARGS = [
    str(SERVER),
    "-m", str(MODEL),
    "--mlock",
    "-t", "2",              # threads
    "-c", "512",            # context length
    "--temp", "1.2",        # temperature
    "--top_p", "0.95",
    "--top_k", "80",
    "--mirostat", "2", 
    "--repeat-penalty", "1.07",
    "--port", "8080",       # HTTP server port
]

def main():
    if not SERVER.exists():
        raise SystemExit(f"[ERROR] llama-server not found: {SERVER}")
    if not MODEL.exists():
        raise SystemExit(f"[ERROR] Model not found: {MODEL}")

    print("[INFO] Launching llama-server…")
    try:
        # Inherit stdout/stderr so you can see server logs in the terminal
        subprocess.run(ARGS, check=False)
    except KeyboardInterrupt:
        print("\n[INFO] Execution interrupted by user (Ctrl+C). Shutting down server...")

if __name__ == "__main__":
    main()