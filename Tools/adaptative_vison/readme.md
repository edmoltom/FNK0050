# Adaptive Vision Detector

This script implements a **low-resolution, adaptive edge-based detection pipeline** designed for stable, real-time performance on embedded systems (e.g., Raspberry Pi).  
It is tuned to detect the most relevant object in a scene even under challenging conditions, with minimal computational cost.

## Detection Strategy

The approach balances **speed** and **stability** over raw precision:

1. **Low-resolution processing**  
   Input is resized to a fixed small resolution (`PROC_W=160`, `PROC_H=120`) for fast computation.

2. **Adaptive Canny edge detection**  
   - Calculates the percentage of edge pixels (`edge_density`).  
   - Adjusts thresholds dynamically to target a density of **~5–10%** (`VIDA_TARGET`), making it robust to lighting changes.

3. **Fallback with adaptive thresholding**  
   - If too few edges are found, a binary threshold based on local image statistics is applied instead.  
   - This ensures some candidate contours are always available.

4. **Morphological filtering**  
   - **Opening**: removes noise and small artifacts.  
   - **Closing**: fills small gaps inside objects.

5. **Contour selection & scoring**  
   - Contours are filtered by geometric metrics:  
     - **Fill ratio** (area vs. bounding box)  
     - **Aspect ratio** (width/height)  
     - **Solidity** (area vs. convex hull)  
   - A weighted score is computed for each contour, selecting the **most likely relevant object**.

6. **Overlay generation**  
   - The chosen contour's bounding box and center are drawn on the original image.  
   - Optionally saves visual output and detection parameters to `./results/` as PNG + JSON.

## Usage

Place your test image in the working directory and run:

```bash
python adaptative_vision.py
```

You can modify constants at the top of the file to adjust detection behaviour.

## Outputs:

Processed image with drawn bounding box (results/output_XXXX.png)

JSON file with detection metrics (results/output_XXXX.json)

Key Parameters
Parameter		Description	Default
PROC_W/H		Processing resolution					160×120
VIDA_TARGET		Target edge density for adaptive Canny	0.07
BORDER_MARGIN	Pixels to ignore near the image edges	6
MORPH_OPEN_K	Kernel size for morphological opening	3
MORPH_CLOSE_K	Kernel size for morphological closing	5

## Strengths
Fast and lightweight — works in real time on Raspberry Pi.

Stable — consistent results even with variable lighting.

Self-contained — minimal dependencies, only OpenCV and NumPy.

## Limitations
Works best when the object has clear edges against the background.

Low resolution means fine details may be lost.

Parameters are tuned for general robustness, not a specific dataset.