# Application services (`Server/app/services`)

Services wrap the interface layer so the runtime can start/stop hardware loops without duplicating
boilerplate. Each service owns the lifecycle of a specific subsystem and exposes convenience
methods to the rest of the application.

## MovementService

- Wraps `interface.MovementControl` and starts its blocking loop in a background thread.
- Provides helpers such as `turn_left`, `turn_right`, `relax`, and delegates any other attribute
  access to the underlying controller through `__getattr__`.
- Used by the social FSM and mind supervisor to keep the robot steady or initiate gestures.

## VisionService

- Owns a `interface.VisionManager` instance and tracks the active pipeline (`object`, `face`, …).
- `register_face_pipeline()` installs a `FacePipeline` with the configuration provided in `app.json`.
- `start()` selects the desired pipeline, limits OpenCV threads to avoid contention, starts the
  camera stream, and registers a frame callback.
- `last_b64()` / `snapshot_b64()` expose encoded frames for WebSocket streaming or debugging.

## ConversationService

- Manages the lifecycle of the llama.cpp process (`mind.llm.process.LlamaServerProcess`).
- Wires Speech-to-Text, Text-to-Speech, LED controller, LLM client, and the conversation manager in
  a dedicated thread.
- Performs readiness checks with configurable timeouts/backoff and exposes a `stop_event` so the
  builder can signal termination from the FSM callbacks.
- Keeps logging metrics about listen time, LLM retries, and LED state transitions.

These services are instantiated by `builder.core_builder.build()` based on the configuration flags
and injected into `AppRuntime` through the `AppServices` container.
