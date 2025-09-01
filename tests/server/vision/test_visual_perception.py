import os
import base64, datetime, time
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Server"))
sys.path.insert(0, str(ROOT))

cv2_stub = types.SimpleNamespace(
    COLOR_RGB2BGR=0,
    cvtColor=lambda frame, code: frame,
    imencode=lambda ext, frame: (True, b"data"),
)
numpy_stub = types.SimpleNamespace(ndarray=object)
sys.modules.setdefault("cv2", cv2_stub)
sys.modules.setdefault("numpy", numpy_stub)

from Server.core.VisionInterface import VisionInterface

def main():
    cam = VisionInterface()
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

