# Servicios de la aplicación

Los servicios actúan como adaptadores entre la lógica de alto nivel y las implementaciones de `core`.

## MovementService

- Instancia `MovementControl` y arranca su bucle bloqueante (`start_loop`) en un hilo en segundo plano mediante `threading.Thread`.
- Expone métodos de conveniencia como `turn_left`, `turn_right`, `relax` y `stop`, delegando directamente en `MovementControl`.
- Implementa `__getattr__` para reenviar cualquier otra llamada al objeto interno, permitiendo acceder a comandos avanzados (p. ej. `walk`, `gesture`, límites de la cabeza).

Este servicio es el responsable de mantener activo el control de movimiento mientras la aplicación esté en ejecución.

## VisionService

- Crea un `VisionManager`, conserva el modo de operación (`object`, `face`, etc.) y los parámetros de cámara (`camera_fps`).
- `register_face_pipeline()` permite registrar dinámicamente un pipeline facial y seleccionarlo si la configuración lo requiere.
- `set_frame_callback()` guarda una función para recibir resultados procesados.
- `start()` inicializa la captura: fija el número de hilos de OpenCV, selecciona el pipeline adecuado, arranca el `VisionManager` y comienza el streaming periódico con el intervalo especificado.
- `stop()` detiene la captura y libera recursos; `last_b64()` y `snapshot_b64()` facilitan recuperar imágenes codificadas para exponerlas por WebSocket u otros canales.

## Integración con el servidor WebSocket

Cuando `enable_ws` está activo, `AppRuntime` invoca `start_ws_server`, que a su vez crea un `websockets.serve` asociado al `VisionService`. Los comandos admitidos (`ping`, `start`, `stop`, `capture`) permiten controlar la captura remota y solicitar la última imagen en base64.

