# Núcleo del servidor (`Server/core`)

El paquete `core` reúne todos los subsistemas de bajo nivel del robot: control de movimiento, visión artificial, síntesis y reconocimiento de voz, integración con modelos de lenguaje, sensorización y utilidades de hardware como los LEDs. La aplicación de alto nivel (`Server/app`) consume estos componentes a través de las clases fachada `MovementControl`, `VisionManager`, `VoiceInterface` y `LedController`.

## Mapa rápido de módulos

| Archivo/Paquete | Propósito principal |
| --- | --- |
| `MovementControl.py` | Fachada síncrona para poner en marcha el controlador de locomoción basado en colas. |
| `VisionManager.py` | Gestión de cámara, pipelines y streaming de detecciones. |
| `VoiceInterface.py` | Orquestación completa STT → LLM → TTS con estados de conversación y feedback por LEDs. |
| `LedController.py` | Envoltura asíncrona sobre `led/led.py` para lanzar animaciones sin bloquear el bucle principal. |
| `movement/` | Implementación completa del controlador: cinemática, CPG, hardware PCA9685, gestos y logging. |
| `vision/` | Pipelines de visión, detectores, perfiles y utilidades para registrar o superponer resultados. |
| `voice/` | Reproductor de efectos (`sfx.py`) y síntesis vía Piper+SoX (`tts.py`). |
| `hearing/` | Reconocimiento de voz en streaming con Vosk y normalización de texto. |
| `llm/` | Cliente HTTP para LLaMA/Qwen, memoria de conversación, “persona” y scripts auxiliares. |
| `sensing/` | Lectura de IMU con fusión de sensores y odometría simplificada. |
| `led/` | Acceso directo al bus SPI de la tira LED (PCB v2) con animaciones básicas. |

A continuación se detalla cada bloque.

---

## Movimiento (`movement/`)

### `MovementControl` y `MovementController`
- `MovementControl` ofrece un API sencillo (`walk`, `turn`, `step`, `head_deg`, `gesture`, etc.) que encola comandos en el `MovementController` subyacente.
- `MovementController` consume la cola, gestiona el estado de locomoción y aplica órdenes al hardware:
  - Mantiene un punto objetivo para cada pata (`point[leg][x|y|z]`) y, tras validar que está dentro de los límites, lo convierte en ángulos con `kinematics.coordinate_to_angle`.
  - Permite comandos continuos (`WalkCmd`, `TurnCmd`) y discretos (`StepCmd`) ajustando un generador de patrones centrales (`GaitRunner`/`CPG`).
  - Incluye control de cabeza con límites configurables, relajación (`RelaxCmd`), reproducción de gestos (`GestureCmd`) y logging opcional.
  - El bucle `start_loop(rate_hz)` realiza `tick()` + `run()` a ~100 Hz; en modo servicio se ejecuta en un hilo dedicado.

### Hardware y cinemática
- `hardware.py` centraliza los dispositivos físicos: servo PCA9685, IMU (`sensing.IMU`), odometría (`sensing.odometry`), PID incremental y CPG. Calcula offsets de calibración a partir de `movement/calibration/point.txt`.
- `servo.py` encapsula el driver `PCA9685` (I²C) y traduce ángulos a ticks.
- `PCA9685.py` implementa el controlador PWM con gestión de errores I²C.
- `kinematics.py` contiene la conversión ángulo↔coordenada y utilidades como `clamp`.
- `posture.py` define posturas y transformaciones (balance, actitud, cambio de altura).
- `data.py` carga/guarda matrices de puntos en texto plano para calibración o edición manual.

### Generación de pasos y gestos
- `gait_cpg.py` implementa un CPG configurable (frecuencia, amplitud XY/Z, duty) con rampas suaves y cálculo de trayectoria pie-suelo.
- `gait_runner.py` traduce el estado del CPG a posiciones de patas, soportando avance, pasos laterales, giros y paradas suaves.
- `gestures.py` reproduce secuencias absolutas (`Sequence` de `Keyframe`) con interpolación lineal y, opcionalmente, overrides de servos. Incluye `GesturePlayer` con hilos para animaciones no bloqueantes y carga de gestos desde JSON (`movement/gestures/*.json`).

### Logging y pruebas
- `logger.py` escribe un CSV con IMU, puntos de patas y odometría sin bloquear el hilo principal (usa `Queue` + `Thread`).
- `test_codes/hello_world.py`, `test_gamepad.py`, etc., ilustran cómo arrancar el controlador y enviar comandos desde distintos dispositivos.

---

## Visión (`vision/`)

### `VisionManager`
- Envuelve una `Camera` (Picamera2 opcional) y gestiona streaming en segundo plano con `CameraWorker`.
- Permite registrar pipelines (`register_pipeline`), seleccionar modo (`select_pipeline`), fijar ROI dinámico y recuperar el último frame procesado en base64 (`get_last_processed_encoded`, `snapshot`).
- Durante el streaming:
  - Restringe los FPS según `camera_fps` (configurable).
  - Ejecuta detecciones cada ≥0,2 s, calcula estadísticas (tiempo de detección/encode, FPS estimados, fracción de ROI) y las registra vía `logging`.

### API y pipelines
- `vision/api.py` mantiene un registro global de pipelines (`object` → `ContourPipeline`, `face` → `FacePipeline`), expone helpers para cambiar perfiles (`load_profile`), ajustar parámetros en caliente (`update_dynamic`) y devolver la última `Result`.
- `pipeline/base_pipeline.py` define la interfaz común (`process` → `Result` con `data` y `timestamp`).
- `pipeline/contour_pipeline.py` coordina dos detectores (`big`/`small`), mantiene estado de estabilidad (EMAs, misses) y utiliza `DynamicAdjuster` para auto-Calibrar Canny.
- `pipeline/face_pipeline.py` usa cascadas Haar de OpenCV con opción de ROI; produce bounding boxes y overlays.
- `detector_registry.py` crea detectores leyendo perfiles JSON (`vision/profiles/profile_big.json`, `profile_small.json`) y guarda el `DynamicAdjuster` asociado.
- `dynamic_adjuster.py` implementa la búsqueda iterativa de umbrales Canny y un rescate con binarización adaptativa si el porcentaje de bordes es bajo.

### Utilidades
- `camera.py` inicializa Picamera2, maneja errores y entrega frames RGB; lanza `CameraCaptureError` tras varios fallos consecutivos.
- `camera_worker.py` captura frames en un hilo, manteniendo el último frame fresco con timestamp.
- `imgproc.py` agrupa funciones de preprocesado, morfología, scoring de contornos y utilidades para ROI.
- `overlays.py` dibuja los resultados (`bbox`, centros, puntuación, caras) y calcula resolución de referencia.
- `viz_logger.py` registra detecciones, overlays y artefactos opcionales (cada `stride` frames) en `runs/vision/…`.
- `engine.py` mantiene compatibilidad con nombres antiguos (`VisionEngine`, `EngineResult`).

---

## Voz y conversación

### Reconocimiento (`hearing/`)
- `stt.py` encapsula Vosk con `SpeechToText`:
  - Usa `sounddevice.RawInputStream` para capturar audio (16 kHz, mono) y `KaldiRecognizer` para decodificar.
  - Filtra resultados por confianza media ≥0,60 y longitud mínima.
  - Permite pausar/reanudar el flujo (`pause`, `resume`) y expone `listen()` como generador infinito.
- `text_norm.py` normaliza puntuación en español (añade signos de interrogación de apertura, asegura cierre con `.?!`).

### Síntesis (`voice/`)
- `tts.py` provee `TextToSpeech`, que localiza modelos Piper (`~/piper/*.onnx`), aplica una cadena de efectos SoX (pitch, compand, phaser, etc.) y reproduce la salida (preferencia `aplay`/`paplay`/`play`). Permite guardar el WAV final opcionalmente.
- `sfx.py` reproduce efectos cortos reusando el mismo mecanismo de detección de reproductores disponibles.

### Integración con LLM (`llm/`)
- `persona.py` define la personalidad “Lumo” (instrucciones de sistema, estado del robot, temas preferidos, fragmentos prohibidos) y parámetros de sampling (`TEMP`, `TOP_P`, `TOP_K`, `MAX_TOKENS`). `postprocess` filtra frases indeseadas y recorta al máximo de caracteres.
- `llm_client.py` envía peticiones HTTP (`/v1/chat/completions`) a un `llama-server` configurable vía `LLAMA_BASE`, con penalización de repetición y stops personalizados.
- `llm_memory.py` mantiene memoria corta de conversación (`ConversationMemory`) para añadir contexto a nuevas consultas.
- `llm_to_tts.py` reutiliza `TextToSpeech` para convertir un prompt único en audio (útil en scripts o tests).
- `start_llama_server.py` lanza el servidor `llama.cpp` con parámetros adecuados para Raspberry Pi (modelo Qwen 0.5B quantizado).

### `VoiceInterface.py`
- Construye `TextToSpeech`, `SpeechToText`, `LedController` y una memoria conversacional global.
- Gestiona estados `WAKE → ATTENTIVE_LISTEN → THINK → SPEAK` con tiempo de atención configurable y cooldown tras hablar.
- Detecta palabras de activación (`WAKE_WORDS`), pausa el STT durante la generación de respuesta, consulta el LLM (`llm_ask`) y reproduce la salida con TTS (`tts_say`).
- Controla LEDs según el estado (`wake`, `listen`, `processing`, `speaking`) usando corrutinas en el bucle de evento propio (`asyncio`).
- Expuesto en `test_codes/test_voice_interface.py` y `test_voice_loop.py` para pruebas manuales o integradas.

---

## Sensores y periferia

### `sensing/IMU.py`
- Accede a un MPU6050, calibra un offset inicial promediando 100 muestras y aplica filtros de Kalman individuales (accel/gyro).
- Realiza fusión de sensores mediante cuaterniones con corrección proporcional–integral (`Kp`, `Ki`) y devuelve `pitch`, `roll`, `yaw` junto a aceleraciones normalizadas.
- Incluye alias `imuUpdate` para compatibilidad con código legado.

### `sensing/odometry.py`
- Mantiene una odometría planar muy ligera (`x`, `y`, `theta`).
- `tick_gait(phase_deg, step_length)` integra desplazamientos en cada evento de zancada (cambia de signo el seno).
- `zupt(is_stance, gyro_z_dps)` implementa una regla de “Zero Velocity Update” cuando la pata está en apoyo y el giro es pequeño.

### LEDs (`LedController.py` y `led/`)
- `led/led.py` controla la tira SPI de 8 LEDs (ajustable) con métodos como `set_all`, `colorWipe`, `rainbow`, `off`.
- `led/spi_ledpixel.py` es el driver directo (`spidev` + `numpy`) que convierte colores a los timings WS2812 compatibles con la PCB v2.
- `LedController` encapsula el acceso en un contexto asíncrono: encola comandos, permite animaciones (`start_pulsed_wipe`, `rainbow`, etc.) y garantiza cierre limpio (`close()`).

---

## Recursos y configuración

- **Calibración movimiento**: `movement/calibration/point.txt` contiene la postura base para ajustar offsets de servos.
- **Gestos**: `movement/gestures/*.json` definen secuencias con keyframes y overrides; hay plantillas y README explicativos en inglés y español.
- **Visión**:
  - `vision/profiles/profile_big.json` y `profile_small.json` contienen parámetros de procesamiento (Canny, morfología, filtros geométricos, color gating).
  - `vision/cascades/haarcascade_frontalface_default.xml` se utiliza para el pipeline facial.
  - `vision/logger_README.md` y `profiles/PROFILE_Readme_ES.md` documentan cómo capturar runs y ajustar perfiles.
- **Audio**: coloca modelos Piper en `~/piper/*.onnx` y (opcionalmente) su JSON de configuración al lado.

---

## Dependencias externas destacadas

- **Movimiento**: `numpy`, `smbus` (hardware real), `asyncio`.
- **Visión**: `opencv-python`, `numpy`, `picamera2` (opcional), `websockets` (para streaming en `Server/app`), `base64`.
- **Voz**: `sounddevice`, `vosk`, `piper`, `sox`, `argparse`.
- **LLM**: `requests` para hablar con `llama-server`.
- **Sensores**: `mpu6050`, `filters.kalman` (está en `Server/lib/filters`), `spidev`.

Recuerda revisar `Server/lib` y `Server/network` si necesitas detalles adicionales (drivers de periféricos, control PID, utilidades de socket), ya que `core` depende de algunas de sus clases.

---

## Cómo se integra con `Server/app`

1. `AppServices` crea una instancia de `MovementControl`, `VisionService` (que a su vez envuelve a `VisionManager`) y `SocialFSM`.
2. El runtime lanza el hilo de movimiento (`MovementController.start_loop`), inicia el streaming de visión (`VisionManager.start_stream`) y registra callbacks de seguimiento (controladores en `Server/app/controllers`).
3. El servicio WebSocket opcional expone `VisionManager.snapshot`/`get_last_processed_encoded` y mapea comandos a los métodos de `MovementControl`.
4. Para experiencias conversacionales, scripts como `test_voice_interface.py` o `run.py` cargan `VoiceInterface.ConversationManager`.

Este documento debería servir como referencia rápida para entender qué hace cada pieza del núcleo y cómo se relaciona con el resto del proyecto.
