# Vision Pipeline — ContourDetector + Temporal API

Resumen conciso del pipeline y tuning. Paridad con `contour_detector.py` y `api.py`.

## Pipeline
1) **Preprocesado** → resize (proc_w,h), gris, blur impar.  
2) **Auto‑Canny** → ajusta `t1` hasta vida ∈ [life_min, life_max]; `t2 = ratio*t1`.  
3) **Rescate** → si vida &lt; rescue_life_min: adaptive threshold OR.  
4) **Color‑gate** (opc.) → `hsv` o `lab_bg`, check de cobertura y OR/AND.  
5) **Pre‑morph** → crop inferior, despeckle, fill_from_edges.  
6) **Morph loop** → CLOSE+Dilate (+OPEN), márgenes; ajusta ck/dk por `fill` y `bbox_ratio`.  
7) **Selección** → filtros geométricos; features; puntuación con pesos + centro.  
8) **Salida** → bbox, center, score, fill, ratio, life, overlay.

## Capa temporal (API)
- Dos detectores: **BIG/SMALL** con estado (`last_bbox`, `score_ema`, `miss_count`).  
- **Histeresis**: ON si `score_ema ≥ on_th`; OFF si cae por `off_th`.  
- **ROI tracking**: detecta en ROI (roi_factor); si `miss_m` fallos ⇒ reset + global.  
- **Retorno**: BIG ok, si no SMALL ok, si no “menos malo”.

## Knobs
- Proc, Canny, Morph, Geo, Weights, Pre‑morph, Color‑gate y Temporal (on/off, thresholds, roi_factor, ema, perfiles).

## Uso
```python
from core.vision.detectors.contour_detector import ContourDetector
det = ContourDetector.from_profile("profile_big_solid.json")
res = det.detect(frame_bgr, return_overlay=True)

from core.vision.api import process_frame
out = process_frame(frame_bgr, return_overlay=True, config={"roi_factor":1.8, "ema":0.7})
```

## Tips rápidos
- Vida muy baja → baja `t1_init` o sube `kp`; muy alta → sube `life_min` o baja `t2_ratio`.  
- Fondos variables → `lab_bg`; objeto cromático → `hsv` + `AND`.  
- Salto de bbox → sube `roi_factor`; nerviosismo → baja `off_th` o sube `ema`.  
