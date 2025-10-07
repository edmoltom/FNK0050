# Visión (`Server/core/vision`)

El paquete de visión implementa la captura de cámara, el enrutado entre pipelines de detección y el registro opcional de artefactos.

## `VisionManager`

`VisionManager` inicia la cámara (`Camera`), registra pipelines, aplica regiones de interés (ROI) y ejecuta un hilo de captura que procesa frames a intervalos configurables. Además codifica los resultados en JPEG/base64, mantiene estadísticas básicas (tiempos de detección/encode, FPS estimados) y delega en un `VisionLogger` cuando está habilitado.​:codex-file-citation[codex-file-citation]{line_range_start=19 line_range_end=200 path=Server/core/VisionManager.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/VisionManager.py#L19-L200"}​

### Captura

- `vision/camera.py`: envuelve Picamera2 (si está disponible) y proporciona `capture_rgb`, devolviendo frames vacíos o lanzando `CameraCaptureError` tras múltiples fallos consecutivos.​:codex-file-citation[codex-file-citation]{line_range_start=23 line_range_end=108 path=Server/core/vision/camera.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/vision/camera.py#L23-L108"}​
- `vision/camera_worker.py`: hilo daemon que actualiza continuamente el último frame y timestamp, limitado por `max_fps`.​:codex-file-citation[codex-file-citation]{line_range_start=10 line_range_end=43 path=Server/core/vision/camera_worker.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/vision/camera_worker.py#L10-L43"}​

## API y pipelines

- `vision/api.py` mantiene un registro global de pipelines (`object`, `face` por defecto), permite registrarlos dinámicamente, seleccionar uno activo y procesar frames con caching de resultados recientes (≤0,2 s). También expone utilidades para recargar perfiles y ajustar parámetros dinámicos.​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=104 path=Server/core/vision/api.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/vision/api.py#L1-L104"}​
- `vision/pipeline/contour_pipeline.py`: combina detectores “big/small” de contornos, gestiona estado de estabilidad (EMA de score, reintentos tras misses) y ajusta dinámicamente los umbrales Canny con `DynamicAdjuster`. Puede recortar a ROI según la bbox previa y reabrir perfiles desde `vision/profiles`.​:codex-file-citation[codex-file-citation]{line_range_start=40 line_range_end=200 path=Server/core/vision/pipeline/contour_pipeline.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/vision/pipeline/contour_pipeline.py#L40-L200"}​
- `vision/pipeline/face_pipeline.py`: pipeline basado en cascadas Haar de OpenCV con preprocesado opcional (equalize + resize), soporte de ROI y generación de overlays. Devuelve un listado de caras con coordenadas normalizadas al espacio del frame.​:codex-file-citation[codex-file-citation]{line_range_start=15 line_range_end=178 path=Server/core/vision/pipeline/face_pipeline.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/vision/pipeline/face_pipeline.py#L15-L178"}​
- `vision/dynamic_adjuster.py`: implementa el auto-Canny con rampas sobre `t1`/`t2`, límites de densidad de bordes (“life”) y un modo de rescate que mezcla Canny con umbral adaptativo cuando el contraste es bajo.​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=79 path=Server/core/vision/dynamic_adjuster.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/vision/dynamic_adjuster.py#L1-L79"}​

## Registro y overlays

`vision/viz_logger.py` crea una carpeta `runs/vision/<timestamp>` y, cada `stride` frames, guarda CSV y artefactos (frame original, overlay, salidas de detector). Se integra con la API para obtener detectores y resultados recientes, generando overlays aun cuando no se reciben desde el pipeline.​:codex-file-citation[codex-file-citation]{line_range_start=13 line_range_end=160 path=Server/core/vision/viz_logger.py git_url="https://github.com/edmoltom/FNK0050/blob/dev/Server/core/vision/viz_logger.py#L13-L160"}​

