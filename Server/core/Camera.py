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
        self._config = {} 
        self._last_encoded_image = None
        self._streaming = False
        self._thread = None

    def set_processing_config(self, config):
        self._config = config

    def capture_array(self):
        self.picam2.start()
        frame = self.picam2.capture_array()
        self.picam2.stop()
        return frame

    def _apply_pipeline(self):
        self.picam2.start()
        frame = self.capture_array()
        self.picam2.stop()
        
        if not self._config:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame  

        if self._config.get("blur", False):
            frame = cv2.GaussianBlur(frame, (5, 5), 0)

        if self._config.get("edges", False):
            frame = cv2.Canny(frame, 50, 150)

        if self._config.get("contours", False):
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            ret, thresh = cv2.threshold(gray, 127, 255, 0)
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contour_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            cv2.drawContours(contour_img, contours, -1, (0, 255, 0), 2)
            frame = contour_img

        return frame

    def start_periodic_capture(self, interval=1.0):
        if self._streaming:
            print("[Camera] Streaming already running.")
            return
        self._streaming = True

        def _capture_loop():
            while self._streaming:
                try:
                    frame = self._apply_pipeline()
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