# Aplicación del servidor

La carpeta `Server/app` orquesta la ejecución del runtime que combina visión artificial, control de movimiento y difusión opcional por WebSocket. Los archivos principales son:

- `application.py`: punto de entrada que prepara el registro, construye los servicios y arranca el runtime principal.
- `builder.py`: fabrica un contenedor `AppServices` a partir de la configuración JSON y crea instancias de visión, movimiento y la lógica social.
- `runtime.py`: coordina el ciclo de vida de los servicios, gestiona la captura de frames, despacha la lógica de interacción y, cuando está habilitado, expone un servidor WebSocket.
- `logging_config.py`: define la política de rotación del fichero `robot.log`.
- `config/app.json`: valores predeterminados de los servicios y la lógica social.

## Flujo de arranque típico

1. `setup_logging()` aplica la configuración de logging y crea (si no existe) el archivo `robot.log`.
2. `build()` lee el JSON de configuración y construye `AppServices` con las banderas `enable_vision`, `enable_movement` y `enable_ws`, además de las opciones específicas para visión y WebSocket.
3. `AppRuntime` recibe las dependencias ya configuradas, registra manejadores de señales y prepara la función que procesará cada frame de vídeo.
4. Al iniciarse, el runtime arranca los servicios habilitados: activa el bucle de movimiento, inicializa la visión y registra un callback para recibir detecciones.
5. Si se habilita WebSocket, se publica un servidor que atiende comandos de control y entrega frames codificados. Si no, el runtime mantiene un bucle de espera hasta que se solicite la parada (por señal o por el propio código).
6. `stop()` detiene con seguridad los servicios, relaja la postura del robot y libera recursos.

## `AppServices` y su configuración

`AppServices` agrupa todo lo que el runtime necesita para ejecutarse. Los atributos más relevantes son:

| Atributo | Descripción | Valor por defecto |
| --- | --- | --- |
| `cfg` | Configuración completa leída del JSON. | `{}` |
| `enable_vision`, `enable_movement`, `enable_ws` | Banderas para activar o desactivar cada subsistema. | `True` |
| `vision_cfg` | Parámetros del pipeline de visión (modo, FPS, perfil de rostro). | `{}` |
| `mode` | Pipeline seleccionado (`object`, `face`, etc.). | `"object"` |
| `camera_fps` | FPS objetivo para la cámara. | `15.0` |
| `face_cfg` | Opciones del detector facial; si está presente se registra un pipeline dedicado. | `{}` |
| `interval_sec` | Intervalo entre capturas consecutivas al hacer `start_stream`. | `1.0` |
| `ws_cfg` | Diccionario con `host` y `port` para el servidor WebSocket. | `{"host": "0.0.0.0", "port": 8765}` |
| `vision`, `movement`, `fsm` | Instancias concretas de `VisionService`, `MovementService` y `SocialFSM` (si se han habilitado). | `None` |

El fichero `config/app.json` ofrece un ejemplo completo: activa todos los subsistemas, selecciona el modo `face`, ajusta el detector con `resize_ratio`, `min_size`, `scale_factor` y `min_neighbors`, y define el comportamiento social (`deadband_x`, `lock_frames_needed`, `miss_release`, `interact_ms`, `relax_timeout`, `meow_cooldown_*`). Puedes copiarlo y adaptarlo a tu entorno.

## Logging y salidas

`setup_logging()` añade un `RotatingFileHandler` con hasta tres archivos de 1 MB cada uno en la raíz del repositorio (`robot.log`). Si vuelves a llamar a la función no se duplicarán manejadores, por lo que es seguro invocarla desde scripts o tests adicionales.

## Relación con controladores y servicios

El runtime delega las decisiones de seguimiento y socialización al módulo `controllers` y utiliza los adaptadores de `services` para hablar con las capas de `core`. La documentación detallada de ambos se encuentra en archivos separados dentro de esta misma carpeta.

