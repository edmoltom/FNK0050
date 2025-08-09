"""
Vision Parameter Tuner (educational)
------------------------------------
A visual tool to understand and compare three basic image processing schemes:
  - CANNY: edge detection (T1/T2 thresholds).
  - ADAPTIVE: adaptive thresholding (local blocks).
  - FIXED: fixed global threshold (T1).

Allows adjusting blur, morphological kernel size, scale, and minimum contour area.
This is meant for exploration and learning, NOT for production use.

Hotkeys:
  - 'm' : switch mode (CANNY → ADAPTIVE → FIXED → ...)
  - 's' : save resulting image + parameters (in ./results_tuner)
  - 'q' or 'ESC' : quit
"""

import os
import json
import cv2
import numpy as np
from datetime import datetime

# ---------------- Basic config ----------------
WIN_MAIN = "Vision Tuner"
WIN_AUX1 = "Preprocess"
WIN_AUX2 = "Binary/Edges"
WIN_AUX3 = "Post-Morph"

TRACKS = {
    "Threshold1": dict(init=50,  max=255),
    "Threshold2": dict(init=150, max=255),
    "Blur":       dict(init=1,   max=20),   # kernel = 2*Blur + 1 (odd)
    "Min Area":   dict(init=100, max=3000),
    "Morph K":    dict(init=0,   max=15),   # square kernel NxN
    "Resize %":   dict(init=100, max=100),  # 1..100 (%)
}

MODE_LABELS = ["CANNY", "ADAPTIVE", "FIXED"]

# ---------------- Load image ----------------
BASE = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE, "base.png")
image = cv2.imread(IMG_PATH)
if image is None:
    raise FileNotFoundError("'base.png' not found in script folder.")

gray_full = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# ---------------- Windows & sliders ----------------
cv2.namedWindow(WIN_MAIN,  cv2.WINDOW_NORMAL)
cv2.namedWindow(WIN_AUX1,  cv2.WINDOW_NORMAL)
cv2.namedWindow(WIN_AUX2,  cv2.WINDOW_NORMAL)
cv2.namedWindow(WIN_AUX3,  cv2.WINDOW_NORMAL)

for name, spec in TRACKS.items():
    cv2.createTrackbar(name, WIN_MAIN, spec["init"], spec["max"], lambda x: None)

print("Controls: 'm' to switch mode | 's' to save | 'q' or 'ESC' to quit")

mode = 0

def get_track(name: str) -> int:
    return int(cv2.getTrackbarPos(name, WIN_MAIN))

def gaussian_blur(img, blur_val: int):
    k = max(1, 2 * blur_val + 1)  # odd, at least 1
    return cv2.GaussianBlur(img, (k, k), 0), k

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

# ---------------- Main loop ----------------
while True:
    t1 = get_track("Threshold1")
    t2 = get_track("Threshold2")
    blur = get_track("Blur")
    min_area = get_track("Min Area")
    morph_k = get_track("Morph K")
    resize_percent = max(1, get_track("Resize %"))

    scale = resize_percent / 100.0
    resized = cv2.resize(gray_full, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    color_resized = cv2.resize(image, (resized.shape[1], resized.shape[0]), interpolation=cv2.INTER_AREA)

    blurred, k_used = gaussian_blur(resized, blur)
    cv2.imshow(WIN_AUX1, blurred)

    # --- Mode selection ---
    label = MODE_LABELS[mode]
    if mode == 1:  # ADAPTIVE
        binimg = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)
        contour_input = binimg
    elif mode == 2:  # FIXED
        _, fixed = cv2.threshold(blurred, t1, 255, cv2.THRESH_BINARY_INV)
        contour_input = fixed
    else:  # CANNY
        edges = cv2.Canny(blurred, t1, t2)
        contour_input = edges

    cv2.imshow(WIN_AUX2, contour_input)

    # --- Optional morphology ---
    post = contour_input.copy()
    if morph_k > 0:
        kernel = np.ones((morph_k, morph_k), np.uint8)
        post = cv2.morphologyEx(post, cv2.MORPH_CLOSE, kernel, iterations=1)
    cv2.imshow(WIN_AUX3, post)

    # --- Contours ---
    contours, _ = cv2.findContours(post, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    output = color_resized.copy()

    valid = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= min_area:
            cv2.drawContours(output, [cnt], -1, (0, 255, 0), 2)
            valid += 1

    hud = f"MODE: {label} | BlurK: {k_used} | MinArea: {min_area} | MorphK: {morph_k} | Scale: {int(resize_percent)}% | CannyT:({t1},{t2})"
    cv2.putText(output, hud, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(output, f"Contours: {valid}", (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 200), 2)

    cv2.imshow(WIN_MAIN, output)

    key = cv2.waitKey(1) & 0xFF
    if key in (27, ord('q')):   # ESC or 'q'
        break
    elif key == ord('s'):
        # Save cleanly in a folder
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(BASE, "results_tuner")
        ensure_dir(out_dir)
        img_name = os.path.join(out_dir, f"tuner_{ts}.png")
        json_name = os.path.join(out_dir, f"tuner_{ts}.json")

        cv2.imwrite(img_name, output)
        params = {
            "mode": label,
            "threshold1": t1,
            "threshold2": t2,
            "blur_val": blur,
            "blur_kernel_used": k_used,
            "min_area": min_area,
            "morph_k": morph_k,
            "resize_percent": int(resize_percent),
        }
        with open(json_name, "w", encoding="utf-8") as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
        print(f"Saved: {img_name} + {json_name}")
    elif key == ord('m'):
        mode = (mode + 1) % len(MODE_LABELS)
        print(f"Mode: {MODE_LABELS[mode]}")

cv2.destroyAllWindows()