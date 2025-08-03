from picamera2 import Picamera2

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_still_configuration())

    def capture_image(self, filename="image.jpg"):
        self.picam2.start_and_capture_file(filename)
        print(f"[Camera] Imagen guardada en {filename}")