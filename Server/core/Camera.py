from picamera2 import Picamera2
from core.vision.api import process_frame

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
        frame_rgb = self.capture_array()               # Picam2 -> RGB
        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)  # detector usa BGR

        res = process_frame(frame, return_overlay=False)
        if res.get("ok"):
            x, y, w, h = res["bbox"]
            # bbox comes in 160x120 → scale to 640x480
            sx = frame.shape[1] / 160.0
            sy = frame.shape[0] / 120.0
            x2, y2, w2, h2 = int(x*sx), int(y*sy), int(w*sx), int(h*sy)

            cv2.rectangle(frame, (x2, y2), (x2+w2, y2+h2), (0,255,0), 2)
            cx, cy = res["center"]
            cv2.circle(frame, (int(cx*sx), int(cy*sy)), 4, (0,255,0), -1)
            cv2.putText(frame, f"sc={res['score']:.2f}", (x2, max(18, y2-6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

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