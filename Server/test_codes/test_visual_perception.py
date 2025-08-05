from Camera import Camera
import datetime
import os

def main():
    cam = Camera()
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"logs/{ts}.jpg"
    os.makedirs("logs", exist_ok=True)
    cam.capture_structural_view(filename)
    print(f"[✓] Imagen guardada en {filename}")

if __name__ == "__main__":
    main()