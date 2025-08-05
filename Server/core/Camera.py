from picamera2 import Picamera2
import cv2

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_still_configuration(
                main={"size": (640, 480)}
            )
        )

    def capture_image(self, filename="image.jpg"):
        self.picam2.start_and_capture_file(filename)
        print(f"[Camera] Image saved in {filename}")

    def capture_array(self):
        self.picam2.start()
        frame = self.picam2.capture_array()
        self.picam2.stop()
        return frame

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
        cv2.drawContours(combined, contours, -1, (255, 0, 0), 2)  # Draw all contours in blue

        if filename:
            cv2.imwrite(filename, combined)
        return combined
