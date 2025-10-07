# Controladores (`app/controllers`)

Los controladores coordinan el comportamiento social y perceptivo del robot.  
Actúan como intermediarios entre los servicios (visión, movimiento, conversación) y las capas de decisión más altas.  
Dentro de esta carpeta se incluyen, entre otros:

- `face_tracker.py`: gestiona el seguimiento visual de rostros y coordina los ejes de movimiento (cabeza y cuerpo).  
- `social_fsm.py`: define la máquina de estados sociales del robot.  
- `tracker.py`: abstrae el control del movimiento y seguimiento del objeto o rostro detectado.  
- `behavior_manager.py`: coordina los modos globales y las prioridades de los subsistemas.

---

## `SocialFSM`: comportamiento social básico

El **SocialFSM** representa la capa de interacción inmediata del robot.  
Define tres estados principales:

| Estado | Descripción |
|---------|-------------|
| `IDLE` | El robot está relajado, sin objetivo de interacción. |
| `ALIGNING` | Se detecta un rostro y se ajusta la orientación de cabeza/cuerpo. |
| `INTERACT` | El rostro está centrado; el robot puede emitir sonidos o gestos sociales. |

### Control dual de pausa

La máquina social ahora dispone de dos niveles de control externo:

1. **Pausa completa (`pause` / `resume`)**  
   - Detiene completamente el bucle social: no se actualizan movimientos, ni rastreo, ni expresiones.  
   - Se usa cuando el robot está *hablando* o *pensando*, para evitar que el cuerpo o la cabeza se muevan durante el discurso.  

2. **Silencio social (`mute_social`)**  
   - Solo desactiva las *reacciones sociales* (como los maullidos), manteniendo activo el seguimiento de rostro.  
   - Permite que el robot mantenga la mirada en su interlocutor mientras escucha, pero sin emitir sonidos ni gestos espontáneos.

Ambos mecanismos son gestionados desde el **BehaviorManager**, lo que garantiza coherencia entre el estado cognitivo del robot y su expresión física.

---

### Ejemplo de flujo

| Estado de conversación | Acción en `SocialFSM` | Efecto visible |
|------------------------|------------------------|----------------|
| `THINK`, `SPEAK` | `pause()` | El robot se inmoviliza y guarda silencio. |
| `ATTENTIVE_LISTEN`, `WAKE` | `resume()` + `mute_social(True)` | El robot sigue mirando, pero no maúlla. |
| `IDLE` o `SOCIAL` | `resume()` + `mute_social(False)` | Recupera su comportamiento natural y expresivo. |

---

## `BehaviorManager`: coordinación de modos globales

El **BehaviorManager** supervisa el estado de los servicios y ajusta el comportamiento global de Lumo.  
Evalúa de forma continua los estados de conversación y aplica decisiones sobre el movimiento, la visión y el FSM social.

### Modos actuales

| Modo | Descripción | Acciones principales |
|------|--------------|---------------------|
| `CONVERSE` | El robot está hablando o pensando. | Pausa total del FSM y rastreo facial detenido. |
| `SOCIAL` | El robot está atento o escuchando. | Rastreo facial activo, reacciones sociales desactivadas. |
| `IDLE` | Sin interacción activa. | FSM completo activo (seguimiento y expresividad). |

La coordinación se realiza sin detener los servicios base (visión, movimiento o conversación).  
Los procesos como el LLM permanecen cargados para evitar latencia y consumo extra.

---

### Interacción entre capas

AppRuntime
├─ VisionService
├─ MovementService
├─ ConversationService
├─ SocialFSM (interacción física)
└─ BehaviorManager (coordinación de modos)

yaml
Copiar código

- El **BehaviorManager** escucha el estado del `ConversationManager` y ajusta el comportamiento global.  
- El **SocialFSM** ejecuta los cambios (pausar, reanudar, silenciar) según las órdenes del manager.  
- El **FaceTracker** y el **ObjectTracker** siguen operando a nivel de visión, sin interrupción, garantizando continuidad visual aunque el comportamiento esté silenciado.

---

### Propósito de la arquitectura

Esta separación entre *percepción, socialización y comportamiento* permite que Lumo:
- Mantenga una coherencia natural entre lo que “piensa”, “oye” y “hace”.  
- Evite movimientos o sonidos incoherentes durante la conversación.  
- Pueda extenderse fácilmente con nuevos modos (por ejemplo, exploración o juego) sin romper la base social.

---