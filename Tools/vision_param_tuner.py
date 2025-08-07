import os
import cv2
import numpy as np

# Load the base image
base_path = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(base_path, "base.png")
image = cv2.imread(img_path)
if image is None:
    raise FileNotFoundError("'base.png' not found in the current directory.")

# Convert to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Create window
cv2.namedWindow("Vision Tuner", cv2.WINDOW_NORMAL)

# Trackbars for Canny
cv2.createTrackbar("Threshold1", "Vision Tuner", 50, 255, lambda x: None)
cv2.createTrackbar("Threshold2", "Vision Tuner", 150, 255, lambda x: None)
cv2.createTrackbar("Blur", "Vision Tuner", 1, 20, lambda x: None)
cv2.createTrackbar("Min Area", "Vision Tuner", 100, 3000, lambda x: None)

while True:
    t1 = cv2.getTrackbarPos("Threshold1", "Vision Tuner")
    t2 = cv2.getTrackbarPos("Threshold2", "Vision Tuner")
    blur = cv2.getTrackbarPos("Blur", "Vision Tuner")
    min_area = cv2.getTrackbarPos("Min Area", "Vision Tuner")

    # Ensure the blur kernel is odd and >= 1
    k = max(1, blur * 2 + 1)
    blurred = cv2.GaussianBlur(gray, (k, k), 0)

    # Canny
    edges = cv2.Canny(blurred, t1, t2)

    # Find contours
    contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    output = image.copy()

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= min_area:
            cv2.drawContours(output, [cnt], -1, (0, 255, 0), 2)

    cv2.imshow("Vision Tuner", output)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    elif key == ord("s"):
        cv2.imwrite("result_contours.png", output)
        print("Image saved as 'result_contours.png'")

cv2.destroyAllWindows()