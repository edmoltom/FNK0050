# Modo Sandbox de Lumo

El **modo sandbox** permite ejecutar todo el sistema de Lumo —incluyendo el `BehaviorManager`, el `SocialFSM` y el pipeline de conversación— sin depender de ningún componente físico.  
En este modo, el robot “vive” dentro de un entorno simulado, donde los sensores y actuadores son reemplazados por servicios *mock* que escriben en el log o usan la consola como interfaz.

---

## 🧠 Propósito

El sandbox actúa como un **laboratorio mental** para Lumo:  
un entorno donde su mente puede funcionar, experimentar y desarrollarse sin cuerpo.  
Está diseñado para:

- Probar nuevos comportamientos y FSMs sin hardware.  
- Depurar el flujo completo de conversación, visión y comportamiento.  
- Permitir que el LLM y el BehaviorManager trabajen con estímulos simulados.  
- Facilitar el desarrollo remoto o en entornos donde no hay acceso al robot físico.

---

## ⚙️ Estructura

```
Server/
 └── sandbox/
      ├── mocks/
      │    ├── mock_led.py
      │    ├── mock_movement.py
      │    ├── mock_vision.py
      │    ├── mock_voice.py
      │    └── __init__.py
      └── sandbox_runtime.py
```

Cada archivo en `mocks/` representa una versión simplificada de los servicios físicos:

| Archivo | Emula | Función |
|----------|--------|----------|
| `mock_vision.py` | Cámara | Genera detecciones falsas de rostros con coordenadas aleatorias. |
| `mock_movement.py` | Motores / servos | Registra en el log los movimientos solicitados por el sistema. |
| `mock_voice.py` | Voz (STT / TTS) | Usa la consola para escuchar (entrada) y hablar (salida). |
| `mock_led.py` | LEDs de estado | Muestra el color o estado actual mediante logs. |

El archivo `sandbox_runtime.py` reemplaza los servicios reales por estos mocks y arranca el runtime normal.
La configuración global vive en `Server/app/app.json`; ahí se elige el modo (`"sandbox"` o `"real"`) y las banderas de servicios.

---

## 🧩 Ejecución

Desde la raíz del proyecto, simplemente ejecuta:

```bash
python Server/sandbox/sandbox_runtime.py
```

El sistema iniciará los servicios simulados y mostrará logs como:

```
[INFO] mock.vision: [MOCK] Vision started
[INFO] behavior.manager: [MODE] IDLE → SOCIAL
[INFO] mock.voice: [YOU]: hola
[INFO] mock.voice: [LUMO]: I heard: hola
[INFO] mock.led: [MOCK-LED] color set to thinking
[INFO] mock.movement: [MOCK] Moving body right at speed 0.2
```

Esto indica que **la mente de Lumo está activa**:
- El BehaviorManager y la FSM se coordinan.  
- El LLM procesa texto de entrada.  
- Los “motores” y LEDs registran sus acciones.  

---

## 🧰 Configuración

El archivo `Server/app/app.json` concentra todas las opciones de la aplicación. Un extracto relevante para el sandbox es:

```json
{
  "mode": "sandbox",
  "enable_vision": true,
  "enable_movement": true,
  "enable_proprioception": true,
  "conversation": {
    "llm_base_url": "http://127.0.0.1:8080"
  }
}
```

Edita ese fichero para alternar entre hardware real (`"mode": "real"`) o mocks, ajustar los servicios habilitados o cambiar la URL del LLM.

---

## 🧩 Extensión y personalización

El modo sandbox está diseñado para crecer junto con Lumo.  
Algunas posibles extensiones:

- **Visualización:** crear una pequeña interfaz (CLI o GUI) que represente la mirada, LED y movimientos.  
- **Eventos personalizados:** añadir scripts que generen estímulos periódicos (voz, detección, fallo de sensor).  
- **Testing automático:** usar los mocks como base para pruebas unitarias de comportamiento.

---

## 🧭 Beneficios

- Desarrollo y depuración sin hardware.  
- Iteraciones rápidas en la lógica de comportamiento.  
- Trazas limpias en `robot.log` o `sandbox.log`.  
- Independencia entre mente (software) y cuerpo (hardware).  

---

## 🧩 Ejemplo de sesión típica

```
python Server/sandbox/sandbox_runtime.py
```

Salida:

```
[MODE] IDLE → SOCIAL
[FSM] IDLE → ALIGNING
[MOCK-LED] color set to listening
[YOU]: ¿Cómo estás, Lumo?
[LUMO]: Estoy funcionando en modo sandbox. ¡Sin servos, pero con muchas ideas!
[MOCK-MOVE] Turning head right
[FSM] ALIGNING → INTERACT
```

---

## 📁 Relación con la aplicación principal

El sandbox usa exactamente las mismas clases y estructura que el runtime normal (`AppRuntime` y `BehaviorManager`).  
La única diferencia es **qué servicios están conectados**.  
Esto garantiza que cualquier comportamiento desarrollado aquí funcionará igual en el robot real.

---

## 🧩 Filosofía

> “Un robot que puede pensarse sin cuerpo está aprendiendo a imaginar.”  
>  
> — *Documentación interna de Lumo*

El sandbox es el espacio donde Lumo puede aprender a imaginar antes de actuar.  
Permite explorar ideas, probar interacciones y observar el comportamiento emergente con total libertad.

---

