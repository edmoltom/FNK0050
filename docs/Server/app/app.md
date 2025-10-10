# Aplicación del servidor

*Part of the FNK0050 Lumo architecture.*

**Purpose:**  
Coordinar el runtime y los servicios cognitivos, garantizando que las órdenes fluyan hacia las capas de `mind/`, `interface/` y `core/` en ese orden.

**Hierarchy:**  
app → mind → interface → core

**Updated:** 2025-10-10

La carpeta `Server/app` orquesta la ejecución del runtime que combina visión artificial, control de movimiento y difusión opcional por WebSocket. Los archivos principales son:

* `application.py`: punto de entrada que prepara el registro, construye los servicios y arranca el runtime principal.
* `builder.py`: fabrica un contenedor `AppServices` a partir de la configuración JSON y crea instancias de visión, movimiento y la lógica social.
* `runtime.py`: coordina el ciclo de vida de los servicios, gestiona la captura de frames, despacha la lógica de interacción y, cuando está habilitado, expone un servidor WebSocket.
* `logging_config.py`: define la política de rotación del fichero `robot.log`.
* `config/app.json`: valores predeterminados de los servicios y la lógica social.

## Flujo de arranque típico

1. `setup_logging()` aplica la configuración de logging y crea (si no existe) el archivo `robot.log`.
2. `build()` lee el JSON de configuración y construye `AppServices` con las banderas `enable_vision`, `enable_movement` y `enable_ws`, además de las opciones específicas para visión y WebSocket.
3. `AppRuntime` recibe las dependencias ya configuradas, registra manejadores de señales y prepara la función que procesará cada frame de vídeo.
4. Al iniciarse, el runtime arranca los servicios habilitados: activa el bucle de movimiento, inicializa la visión y registra un callback para recibir detecciones.
5. Si se habilita WebSocket, se publica un servidor que atiende comandos de control y entrega frames codificados. Si no, el runtime mantiene un bucle de espera hasta que se solicite la parada (por señal o por el propio código).
6. `stop()` detiene con seguridad los servicios, relaja la postura del robot y libera recursos.

## `AppServices` y su configuración

`AppServices` agrupa todo lo que el runtime necesita para ejecutarse. Los atributos más relevantes son:

| Atributo                                        | Descripción                                                                                      | Valor por defecto                   |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------- |
| `cfg`                                           | Configuración completa leída del JSON.                                                           | `{}`                                |
| `enable_vision`, `enable_movement`, `enable_ws` | Banderas para activar o desactivar cada subsistema.                                              | `True`                              |
| `vision_cfg`                                    | Parámetros del pipeline de visión (modo, FPS, perfil de rostro).                                 | `{}`                                |
| `mode`                                          | Pipeline seleccionado (`object`, `face`, etc.).                                                  | `"object"`                          |
| `camera_fps`                                    | FPS objetivo para la cámara.                                                                     | `15.0`                              |
| `face_cfg`                                      | Opciones del detector facial; si está presente se registra un pipeline dedicado.                 | `{}`                                |
| `interval_sec`                                  | Intervalo entre capturas consecutivas al hacer `start_stream`.                                   | `1.0`                               |
| `ws_cfg`                                        | Diccionario con `host` y `port` para el servidor WebSocket.                                      | `{"host": "0.0.0.0", "port": 8765}` |
| `vision`, `movement`, `fsm`                     | Instancias concretas de `VisionService`, `MovementService` y `SocialFSM` (si se han habilitado). | `None`                              |

El fichero `config/app.json` ofrece un ejemplo completo: activa todos los subsistemas, selecciona el modo `face`, ajusta el detector con `resize_ratio`, `min_size`, `scale_factor` y `min_neighbors`, y define el comportamiento social (`deadband_x`, `lock_frames_needed`, `miss_release`, `interact_ms`, `relax_timeout`, `meow_cooldown_*`). Puedes copiarlo y adaptarlo a tu entorno.

## Logging y salidas

`setup_logging()` añade un `RotatingFileHandler` con hasta tres archivos de 1 MB cada uno en la raíz del repositorio (`robot.log`). Si vuelves a llamar a la función no se duplicarán manejadores, por lo que es seguro invocarla desde scripts o tests adicionales.

## Relación con controladores y servicios

El runtime delega las decisiones de seguimiento y socialización al módulo `controllers` y utiliza los adaptadores de `services` para hablar con la capa `interface/` (por ejemplo, `MovementControl`, `VisionManager`, `VoiceInterface` y `LedController`), que es la responsable de mediar con `core`. La documentación detallada de ambos se encuentra en archivos separados dentro de esta misma carpeta.

---

### Capa de comportamiento global (`BehaviorManager`)

A partir de las versiones recientes, la aplicación incorpora un **gestor de comportamiento** (`BehaviorManager`) que actúa como capa de coordinación entre los distintos controladores.
Su función no es reemplazar la lógica interna de los servicios, sino **observarlos y decidir qué subsistema tiene prioridad** en cada momento.

#### Jerarquía funcional

```
AppRuntime
 ├─ VisionService
 ├─ MovementService
 ├─ ConversationService
 ├─ SocialFSM
 └─ BehaviorManager  ← coordina los anteriores
```

* **AppRuntime** sigue siendo quien enciende y apaga los servicios.
* **BehaviorManager** no crea ni destruye procesos; solo supervisa los estados y envía órdenes suaves (pausar, relajar, reactivar).
* **Los servicios** (por ejemplo, el modelo LLM o la cámara) permanecen activos durante toda la ejecución para evitar sobrecargas innecesarias.

#### Lógica de coordinación

El método interno `_coordinate_behavior()` ejecuta un bucle periódico (por defecto, cada 0.5 s) y toma decisiones simples basadas en el estado actual de la conversación:

| Estado de conversación     | Modo global  | Acción                                               |
| -------------------------- | ------------ | ---------------------------------------------------- |
| `THINK`, `SPEAK`           | **CONVERSE** | Detiene movimiento y pausa el rastreo facial.        |
| `ATTENTIVE_LISTEN`, `WAKE` | **SOCIAL**   | Activa el rastreo facial y libera el movimiento.     |
| Cualquier otro estado      | **IDLE**     | Relaja la postura y mantiene el rastreo desactivado. |

Cada cambio de modo se registra en el log como una transición legible, por ejemplo:

```
Behavior mode: IDLE → SOCIAL
```

#### Propósito

Esta capa permite separar la **lógica global del comportamiento** de la **lógica interna de cada módulo**.
El resultado es un sistema más comprensible: basta con leer `_coordinate_behavior()` para entender qué está haciendo el robot a nivel general, sin sumergirse en los detalles del movimiento, la visión o el flujo conversacional.

A largo plazo, esta arquitectura facilita añadir nuevas “máquinas de estado” o comportamientos (exploración, emociones, aprendizaje) sin romper los subsistemas existentes.

---
**See also:**
- [App Layer](../app/app.md)
- [Mind Layer](../mind/mind.md)
- [Interface Layer](../interface/interface.md)
- [Core Layer](../core/core.md)
