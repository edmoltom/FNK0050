
import os
import cv2
import numpy as np
from datetime import datetime

base_path = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(base_path, "base.png")
image = cv2.imread(img_path)
if image is None:
    raise FileNotFoundError("'base.png' not found in the expected path.")

gray_full = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

cv2.namedWindow("Vision Tuner", cv2.WINDOW_NORMAL)
cv2.createTrackbar("Threshold1", "Vision Tuner", 50, 255, lambda x: None)
cv2.createTrackbar("Threshold2", "Vision Tuner", 150, 255, lambda x: None)
cv2.createTrackbar("Blur", "Vision Tuner", 1, 20, lambda x: None)
cv2.createTrackbar("Min Area", "Vision Tuner", 100, 3000, lambda x: None)
cv2.createTrackbar("Morph Kernel", "Vision Tuner", 0, 10, lambda x: None)
cv2.createTrackbar("Resize %", "Vision Tuner", 100, 100, lambda x: None)

mode = 0
mode_labels = ["CANNY", "ADAPTIVE", "FIXED"]

print("Press 'm' to switch between modes.")
print("Press 's' to save the image and settings.")
print("Press 'q' to exit.")

while True:
    t1 = cv2.getTrackbarPos("Threshold1", "Vision Tuner")
    t2 = cv2.getTrackbarPos("Threshold2", "Vision Tuner")
    blur = cv2.getTrackbarPos("Blur", "Vision Tuner")
    min_area = cv2.getTrackbarPos("Min Area", "Vision Tuner")
    morph_size = cv2.getTrackbarPos("Morph Kernel", "Vision Tuner")
    resize_percent = max(1, cv2.getTrackbarPos("Resize %", "Vision Tuner"))

    scale = resize_percent / 100.0
    resized = cv2.resize(gray_full, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    color_resized = cv2.resize(image, (resized.shape[1], resized.shape[0]), interpolation=cv2.INTER_AREA)

    k = max(1, blur * 2 + 1)
    blurred = cv2.GaussianBlur(resized, (k, k), 0)
    cv2.imshow("Blurred", blurred)

    if mode == 1:
        binarized = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                          cv2.THRESH_BINARY_INV, 11, 2)
        contour_input = binarized
        cv2.imshow("Binarized", binarized)

    elif mode == 2:
        _, fixed = cv2.threshold(blurred, t1, 255, cv2.THRESH_BINARY_INV)
        contour_input = fixed
        cv2.imshow("Binarized", fixed)

    else:
        edges = cv2.Canny(blurred, t1, t2)
        contour_input = edges
        cv2.imshow("Edges", edges)

    if morph_size > 0:
        kernel = np.ones((morph_size, morph_size), np.uint8)
        contour_input = cv2.morphologyEx(contour_input, cv2.MORPH_CLOSE, kernel)
        cv2.imshow("Post-Morph", contour_input)

    contours, _ = cv2.findContours(contour_input.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    output = color_resized.copy()

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= min_area:
            cv2.drawContours(output, [cnt], -1, (0, 255, 0), 2)

    label = mode_labels[mode]
    cv2.putText(output, f"MODE: {label}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.imshow("Vision Tuner", output)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break
    elif key == ord("s"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"result_contours_{timestamp}"
        cv2.imwrite(base_name + ".png", output)
        with open(base_name + ".txt", "w") as f:
            f.write(f"Mode: {label}\n")
            f.write(f"Threshold1: {t1}\n")
            f.write(f"Threshold2: {t2}\n")
            f.write(f"Blur: {blur}\n")
            f.write(f"Min Area: {min_area}\n")
            f.write(f"Morph Kernel: {morph_size}\n")
            f.write(f"Resize %: {resize_percent}\n")
        print(f"Image saved as '{base_name}.png'")
        print(f"Parameters saved as '{base_name}.txt'")

    elif key == ord("m"):
        mode = (mode + 1) % 3
        print(f"Mode changed to: {mode_labels[mode]}")

cv2.destroyAllWindows()
