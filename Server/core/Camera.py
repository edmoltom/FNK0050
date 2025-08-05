from picamera2 import Picamera2
import cv2
import base64
import threading
import time

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_still_configuration(
                main={"size": (640, 480)}
            )
        )
        self._last_encoded_image = None
        self._streaming = False
        self._thread = None

    def capture_image(self, filename="image.jpg"):
        self.picam2.start_and_capture_file(filename)
        print(f"[Camera] Image saved in {filename}")

    def capture_array(self):
        self.picam2.start()
        frame = self.picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.picam2.stop()
        return frame

    def capture_encoded(self):
        """
        Captures an image and returns it encoded as a base64 (string) JPEG.
        """
        frame = self.capture_array()
        _, buffer = cv2.imencode('.jpg', frame)
        img_str = base64.b64encode(buffer).decode("utf-8")
        return img_str

    def capture_structural_view(self, filename=None):
        """
        Captures a structural view of the environment, emphasizing edges and closed contours.
        Optionally saves the image with contours overlaid.
        """
        
        self.picam2.start()
        frame = self.picam2.capture_array()
        self.picam2.stop()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.4)
        edges = cv2.Canny(blurred, 30, 100)  # Edge detection
        dilated = cv2.dilate(edges, None)  # Strengthen edges

        edges_bgr = cv2.cvtColor(dilated, cv2.COLOR_GRAY2BGR)  # Convert edges to 3-channel
        combined = cv2.addWeighted(frame, 0.8, edges_bgr, 0.8, 0)  # Overlay edges on original

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(combined, contours, -1, (0, 0, 255), 2)  # Draw all contours in blue (red before RGB conersion!)
        
        combined = cv2.cvtColor(combined, cv2.COLOR_BGR2RGB)
        
        if filename:
            cv2.imwrite(filename, combined)
        return combined

    def start_periodic_capture(self, interval=1.0):
        if self._streaming:
            print("[Camera] Streaming already running.")
            return
        self._streaming = True

        def _capture_loop():
            while self._streaming:
                try:
                    frame = self.capture_structural_view()
                    _, buffer = cv2.imencode('.jpg', frame)
                    self._last_encoded_image = base64.b64encode(buffer).decode("utf-8")
                except Exception as e:
                    print(f"[Camera] Error in periodic capture: {e}")
                time.sleep(interval)

        self._thread = threading.Thread(target=_capture_loop, daemon=True)
        self._thread.start()
        print("[Camera] Started periodic structural capture.")  

    def stop_periodic_capture(self):
        self._streaming = False
        if self._thread:
            self._thread.join()
            self._thread = None
        print("[Camera] Stopped periodic capture.")  

    def get_last_processed_encoded(self):
        return self._last_encoded_image