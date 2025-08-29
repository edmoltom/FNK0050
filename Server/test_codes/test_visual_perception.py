import os
import sys
import base64, datetime, time

# Ensure the Server package is on the Python path when run directly
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.VisionInterface import VisionInterface

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
