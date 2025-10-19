# Lumo system architecture

*Part of the FNK0050 project.*

**Hierarchy:** `app → mind → interface → core`

## Overview

The server side of the project is organised as a stack of layers that separate orchestration,
cognition, hardware facades, and low-level drivers. The goal is to keep experiments easy to wire
in (through mocks or the sandbox) while preserving a clear flow of data from the “brain” to the
physical body.

```
AppRuntime ──► MindContext ──► Interface facades ──► Core drivers
        ▲                ▲
        │                └── SensorGateway feeds proprioception back to the mind
        └────── configuration & service builders
```

- **App layer (`Server/app`)** bootstraps the runtime, loads configuration from JSON, and wires the
  enabled services (vision, movement, conversation, WebSocket streaming).
- **Mind layer (`Server/mind`)** hosts the persona, LLM client, memory, and the
  `MindSupervisor` that decides how to react to the current context.
- **Interface layer (`Server/interface`)** exposes high-level classes (`MovementControl`,
  `VisionManager`, `VoiceInterface`, `SensorGateway`, etc.) that abstract hardware details.
- **Core layer (`Server/core`)** contains the robot drivers: gait control, vision pipelines,
  speech synthesis/recognition, LED animations, and sensor code.

## Runtime flow

1. `AppRuntime` reads `app.json`, builds an `AppServices` container, and registers signal handlers.
2. When `start()` is called it spins up:
   - `SensorController` + `SensorGateway` to stream IMU/odometry packets into the mind’s
     `BodyModel`.
   - Optional movement/vision/conversation services depending on the configuration flags.
   - An asynchronous WebSocket server if camera streaming is enabled.
3. `initialize_mind()` constructs a `MindContext` with the configured LLM endpoint, persona, and a
   `MindSupervisor`. The supervisor keeps a `SocialFSM` attached whenever vision and movement are
   available.
4. Video frames processed by the vision service are forwarded to the FSM, which aligns the body to
   detected faces and emits meows when interaction rules are satisfied. The supervisor pauses the
   FSM while the voice subsystem is speaking.
5. Conversation support (when enabled) is handled by `ConversationService`: it starts/stops the
   llama.cpp binary, wires Speech-to-Text/Text-to-Speech, synchronises LEDs, and exposes hooks for
   the FSM to trigger speech.

The stack is intentionally modular. Any layer can be mocked (the sandbox replaces the hardware
facades) and the `MindContext` can be reused in tests or tooling.

## Key modules

| Layer | Location | Highlights |
| ----- | -------- | ---------- |
| App | `Server/app/application.py`, `runtime.py`, `builder/` | Entry points, JSON configuration loader, service wiring, WebSocket loop. |
| Mind | `Server/mind/context.py`, `supervisor.py`, `behavior/social_fsm.py` | Persona + LLM client creation, behaviour supervisor, social FSM reacting to vision detections. |
| Interface | `Server/interface/MovementControl.py`, `VisionManager.py`, `VoiceInterface.py`, `sensor_gateway.py` | High-level facades that keep blocking loops and resource management out of the mind layer. |
| Core | `Server/core/movement`, `vision`, `voice`, `hearing`, `sensing`, `led` | Low-level drivers and pipelines used by the interface facades. |

## Extensibility notes

- **Conversation**: the builder honours a rich set of options (`health_timeout`,
  `health_check_backoff`, `max_parallel_inference`, etc.) so the llama.cpp server can be tuned for
  different hosts.
- **Sensors**: new sensors can publish into the `BodyModel` by extending `SensorController` and
  calling `SensorGateway._publish_packet` with the appropriate schema.
- **Sandbox**: `Server/sandbox/sandbox_runtime.py` injects mocks for every interface, making it easy
  to test the mind without hardware.

See the individual layer documents for deeper dives into the services, controllers, and behaviour
logic.
