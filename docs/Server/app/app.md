# Server application layer (`Server/app`)

*Part of the FNK0050 Lumo architecture.*

The application layer glues together configuration, runtime services, and the mind stack. It is
responsible for reading `app.json`, instantiating hardware facades or mocks, and keeping the main
loop responsive to shutdown signals.

## Key files

- `application.py` – CLI entry point that sets up logging and launches `AppRuntime`.
- `runtime.py` – Coordinates services during execution (vision, movement, conversation, WebSocket,
  sensors) and maintains the link with the mind.
- `builder/` – Functions that read JSON configuration and return an `AppServices` container with the
  requested services already instantiated.
- `services/` – Lightweight wrappers around the interface layer that provide lifecycle helpers for
  vision, movement, and conversation.
- `tests/` – Unit tests covering the runtime behaviour, WebSocket handler, and conversation wiring.

## `AppServices`

`builder/core_builder.py` defines a dataclass that collects every configurable aspect of the
runtime. After calling `build()` you get a ready-to-use container with these notable attributes:

| Attribute | Description |
| --------- | ----------- |
| `cfg` | Raw JSON configuration. |
| `runtime_mode` | `"sandbox"` or `"real"`; selects real hardware or mocks. |
| `enable_vision`, `enable_movement`, `enable_ws`, `enable_conversation` | Feature flags toggled from the config file. |
| `vision_cfg` | Mode, FPS, and face detector profile for the camera pipeline. |
| `ws_cfg` | Host/port for the optional WebSocket server. |
| `conversation_cfg` | Llama binary/model paths, health checks, and concurrency limits. |
| `vision`, `movement`, `conversation`, `fsm` | Instantiated services ready to attach to the runtime (may be `None` if disabled). |

When conversation support is enabled the builder also wires callbacks so the `SocialFSM` can trigger
`ConversationService.start()`/`stop()` during interactions.

## Runtime lifecycle

`AppRuntime.start()` performs the following steps:

1. Create (if needed) a `SensorController` and `SensorGateway` so IMU/odometry updates reach the
   mind’s `BodyModel`.
2. Attach the configured vision, voice, movement, and social FSM instances to the `MindContext` via
   `mind.initialize_mind()`.
3. Start the movement thread (if enabled) and relax the robot.
4. Register a frame handler with the vision service so detections update the FSM and the supervisor.
5. Launch the conversation service, including llama.cpp readiness checks and LED state management.
6. Optionally start the WebSocket server that streams frames and receives simple commands.
7. Keep calling `MindSupervisor.update()` until a shutdown event or signal is received.

`stop()` gracefully tears down services in reverse order and joins any background threads.

## Configuration tips

- Set `conversation.enable` to `false` when the llama binary or GGUF file is not available; the
  builder automatically records the reason in `conversation_disabled_reason`.
- Tune `vision.interval_sec` to control how often frames are processed when streaming.
- Face tracking behaviour is configured under `behavior.social_fsm` (deadband, interact timings,
  cooldowns); these values are passed to the FSM by the builder.

## Tests

The application layer ships with focused tests under `Server/tests/`:

- `test_app_runtime.py` ensures the runtime starts/stops services and invokes callbacks.
- `test_app_runtime_conversation_integration.py` checks the conversation lifecycle with mocks.
- `test_llm_client.py` and `test_llama_server_process.py` cover the LLM client and process wrapper
  used by the builder.

Run them with `pytest Server/tests` from the repository root.
