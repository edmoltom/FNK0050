# Vision Parameter Tuner (Educational Tool)

This tool is an interactive OpenCV-based application for exploring and understanding basic image processing techniques.  
It lets you experiment with edge detection and thresholding methods in real time, while adjusting parameters through sliders.

## Features

- **Three processing modes:**
  - **CANNY:** Edge detection with adjustable thresholds `T1` and `T2`.
  - **ADAPTIVE:** Adaptive thresholding using local neighborhoods.
  - **FIXED:** Fixed global threshold using `T1`.

- Adjustable parameters:
  - **Threshold1** / **Threshold2** (used in Canny or Fixed modes)
  - **Blur:** Gaussian blur kernel size
  - **Min Area:** Minimum contour area to display
  - **Morph K:** Morphological close kernel size
  - **Resize %:** Scale the image for faster experimentation

- **Multiple windows** to visualize:
  - Preprocessed image (blurred)
  - Binary/edge image after thresholding
  - Image after optional morphology
  - Final image with contours drawn and a parameter HUD

- Save results:
  - Press `s` to save the final image and all parameters to `./results_tuner/`
  - Images are saved as PNG, parameters as JSON

## Hotkeys

| Key        | Action                                          |
|------------|-------------------------------------------------|
| **m**      | Switch between modes (CANNY → ADAPTIVE → FIXED) |
| **s**      | Save result image + parameters                  |
| **q** / **ESC** | Quit the application                       |

## Requirements

- Python 3.x  
- [OpenCV](https://opencv.org/) (`pip install opencv-python`)  
- NumPy (`pip install numpy`)

## Usage

Place your test image as `base.png` in the same folder as the script.

Run:
```bash
python vision_param_tuner.py

Adjust sliders and switch between modes using the hotkeys above.
Experiment with different combinations to see how parameters affect contour detection.

Example
Example screenshot with Canny mode enabled and tuned parameters:

(You can add a screenshot here after running the tuner)

Note: This is an educational tool meant for exploration and understanding of image processing concepts.
It is not optimized for production use.
