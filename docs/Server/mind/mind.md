# Mind layer (`Server/mind`)

*Part of the FNK0050 Lumo architecture.*

The mind layer concentrates the cognitive pieces of the system: persona definition, LLM access,
short-term memory, and the supervisor that coordinates social behaviour. It is intentionally kept
independent from hardware so it can be reused in tests or the sandbox.

## Entry points

- `context.py` – defines `MindContext`, a façade that wires persona, LLM client, memory, and the
  supervisor. It exposes helpers to attach runtime interfaces (`vision`, `voice`, `movement`,
  `social`).
- `supervisor.py` – implements `MindSupervisor`, responsible for pausing/resuming the social FSM
  while the voice subsystem is speaking and for keeping the body relaxed when idle.
- `__init__.py` – provides `initialize_mind()` and lazy imports so higher layers can access the mind
  components without circular dependencies.

## Sub-packages

- `behavior/` – home of `social_fsm.py`, a face-tracking driven finite state machine that reacts to
  detections by aligning the robot and triggering simple interactions (meows, callbacks).
- `communication/` – builders for bridging the LLM with Text-to-Speech and Speech-to-Text stacks.
- `llm/` – HTTP client, llama.cpp process wrapper, conversation memory, and configuration defaults.
- `perception/` – perception helpers such as the reusable `FaceTracker` used by the FSM.
- `proprioception/` – the `BodyModel` that fuses IMU and odometry data streamed through the
  `SensorGateway`.

## Typical usage

`AppRuntime` calls `initialize_mind(cfg, vision=..., voice=..., movement=..., social=...)` once the
services have been built. The returned `MindContext` offers a `summary()` for quick diagnostics and a
`supervisor` attribute with the orchestration logic. As the runtime starts or stops services it can
call `attach_interfaces()` to keep the mind wired to the latest instances.

The separation between mind and interface layers makes it straightforward to swap physical hardware
for mocks, or to run the mind remotely while streaming detections over the network.
