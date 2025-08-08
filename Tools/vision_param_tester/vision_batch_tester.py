
import os
import cv2
import numpy as np
from pathlib import Path

base_path = os.path.dirname(os.path.abspath(__file__))
param_file = os.path.join(base_path, "config.txt")
image_folder = os.path.join(base_path, "./image_set") 
output_folder = os.path.join(base_path, "./output")

os.makedirs(output_folder, exist_ok=True)

def load_params(filename):
    params = {}
    with open(filename, 'r') as f:
        for line in f:
            if '=' in line:
                key, val = line.strip().split('=')
                val = val.strip()
                try:
                    val_parsed = int(val)
                except ValueError:
                    try:
                        val_parsed = float(val)
                    except ValueError:
                        val_parsed = val  # dejar como string
                params[key.strip()] = val_parsed
    return params

# Cargar parámetros
params = load_params(param_file)
params.setdefault('blur', 3)
params.setdefault('min_area', 100)
params.setdefault('mode', 'ADAPTIVE')

# Procesar imágenes
for filename in os.listdir(image_folder):
    if filename.lower().endswith((".png", ".jpg", ".jpeg")):
        print(f"Procesando: {filename}")
        img_path = os.path.join(image_folder, filename)
        img = cv2.imread(img_path)
        if img is None:
            print(f"⚠️ No se pudo leer {filename}")
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ksize = params['blur'] * 2 + 1
        blurred = cv2.GaussianBlur(gray, (ksize, ksize), 0)

        mode = params['mode'].upper()
        if mode == "CANNY":
            th = cv2.Canny(blurred, 50, 150)
        elif mode == "FIXED":
            _, th = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY_INV)
        else:
            th = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)

        kernel = np.ones((3, 3), np.uint8)
        morph = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filtered = [cnt for cnt in contours if cv2.contourArea(cnt) > params['min_area']]

        cv2.drawContours(img, filtered, -1, (0, 255, 0), 2)
        name, ext = os.path.splitext(filename)
        out_path = os.path.join(output_folder, f"{name}_processed.png")
        cv2.imwrite(out_path, img)
    else:
        print(f"Ignorado (no es imagen): {filename}")
