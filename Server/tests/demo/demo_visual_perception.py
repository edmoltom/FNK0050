from __future__ import annotations

import base64
import datetime
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SERVER_ROOT = PROJECT_ROOT / "Server"

for path in (PROJECT_ROOT, SERVER_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from Server.interface.VisionManager import VisionManager

def main():
    cam = VisionManager()
    os.makedirs("logs", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"logs/{ts}.jpg"

    cam.start()
    cam.start_stream(interval_sec=0.2)
    deadline = time.time() + 3.0
    encoded = None
    while time.time() < deadline and not encoded:
        encoded = cam.get_last_processed_encoded()
        time.sleep(0.05)
    cam.stop()

    if not encoded:
        raise RuntimeError("No se obtuvo imagen procesada a tiempo.")
    with open(filename, "wb") as f:
        f.write(base64.b64decode(encoded))
    print(f"[✓] Imagen guardada en {filename}")

if __name__ == "__main__":
    main()

