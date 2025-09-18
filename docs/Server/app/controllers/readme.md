# Controladores de la aplicación

Los controladores encapsulan la lógica de seguimiento y socialización que se ejecuta sobre las detecciones que llegan desde visión.

## Utilidades genéricas (`tracker.py`)

El archivo define funciones auxiliares para seleccionar objetivos:

- `_extract_targets` y `_select_largest_box` filtran y priorizan la lista de `targets` o `faces` proporcionada por la visión.
- `_extract_space` extrae el tamaño de la imagen (`width`, `height`) para normalizar errores y calcular centros.

### `AxisXTurnController`

Gestiona los giros sobre el eje horizontal cuando el objetivo se desplaza lateralmente. Ajustes destacados:

| Parámetro | Propósito | Valor inicial |
| --- | --- | --- |
| `deadband_x` | Margen de error permitido antes de iniciar un giro. | `0.12` |
| `k_turn` | Ganancia para escalar el pulso en función del error normalizado. | `0.8` |
| `base_pulse_ms` / `min_pulse_ms` / `max_pulse_ms` | Controlan la duración del pulso enviado a `MovementControl.turn_left/turn_right`. | `120 / 60 / 180` ms |
| `turn_speed` | Velocidad aplicada durante el giro en el plano. | `0.3` |

El método `update()` aplica un enfriamiento interno para evitar giros continuos y delega la acción en `MovementControl`.

### `AxisYHeadController`

Controla la inclinación vertical de la cabeza. Combina un filtro exponencial para suavizar el centro del rostro y un PID incremental:

| Parámetro | Descripción |
| --- | --- |
| `pid` (`Incremental_PID(20.0, 0.0, 5.0)`) | Calcula el delta angular. |
| `pid_scale` | Escala la salida del PID (`0.1`). |
| `ema_alpha` | Peso del nuevo centro detectado (`0.2`). |
| `error_threshold` | Margen de error aceptable antes de mover la cabeza (`0.05`). |
| `delta_limit_deg` | Límite de grados por actualización (`3.0`). |
| `recenter_speed_deg` / `recenter_duration_ms` | Controlan la reciente con el tiempo. |

El controlador mantiene el ángulo actual, llama a `MovementControl.head_deg` y ofrece `recenter()` para volver gradualmente al centro tras perder el objetivo.

### `ObjectTracker`

Coordina ambos ejes y mantiene el estado del objetivo:

- Lleva contadores de detecciones consecutivas para fijar (`lock`) o liberar (`miss_release`) el objetivo.
- Cuando pierde rostros, reinicia la posición vertical, detiene el movimiento y puede recentrar la cabeza.
- Al detectar un rostro, calcula el error horizontal (`ex`) y actualiza ambos ejes. Si dispone de `VisionManager`, ajusta la ROI para concentrar la búsqueda alrededor del objetivo bloqueado.

### `FaceTracker`

Proporciona una interfaz compatible con versiones anteriores sobre `ObjectTracker`. Reexpone propiedades (`deadband_x`, `enable_x`, `base_pulse_ms`, etc.) y delega `update()` al rastreador interno. Está pensado para integrarse con servicios que todavía esperan la API de `MovementControl` y `VisionManager`.

## `SocialFSM`

Implementa una máquina de estados sencilla para reaccionar ante rostros alineados:

- **Estados**: `IDLE`, `ALIGNING`, `INTERACT`.
- **Transiciones**: pasa a `ALIGNING` al detectar un rostro; entra en `INTERACT` tras acumular `lock_frames_needed` frames dentro del `deadband_x`; regresa a `IDLE` al perder caras durante `miss_release` frames o al agotar `interact_ms`.
- **Acciones**: usa `MovementService` para detenerse o relajarse tras periodos de inactividad, delega el seguimiento en `FaceTracker` y reproduce el sonido `meow.wav` con un cooldown aleatorio cuando entra en `INTERACT`.

Los parámetros (`deadband_x`, `miss_release`, `interact_ms`, `relax_timeout`, `meow_cooldown_min/max`) se leen del bloque `behavior.social_fsm` de la configuración.

