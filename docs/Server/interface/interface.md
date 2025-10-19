# Interface layer (`Server/interface`)

*Part of the FNK0050 Lumo architecture.*

The interface layer provides high-level facades that shield the mind from hardware-specific
details. Each facade owns the lifecycle of the underlying driver (threads, async loops, device
handles) and exposes a Pythonic API to the application layer.

## Main modules

- `MovementControl.py` – wraps the gait controller from `core.movement`, offering commands such as
  `walk`, `turn`, `relax`, `gesture`, and head positioning with built-in safety limits.
- `VisionManager.py` – manages camera access, pipeline registration, and frame streaming. It exposes
  base64 snapshots used by the WebSocket server and face tracking.
- `VoiceInterface.py` – bridges Speech-to-Text, the LLM client, Text-to-Speech, and LED feedback.
  Implements the wake/think/speak loop, wake-word detection, and LED state transitions.
- `LedController.py` – asynchronous helper around the SPI LED strip driver, enabling non-blocking
  animations and simple colour presets.
- `sensor_controller.py` / `sensor_gateway.py` – read IMU & odometry data and publish it to the
  mind’s `BodyModel` at a configurable frequency.

## Responsibilities

1. Translate high-level intents from the mind into hardware-aware commands.
2. Normalise sensor data before it reaches `mind.proprioception`.
3. Provide mock-friendly APIs so the sandbox can replace them without touching application logic.
4. Keep the dependency chain one-directional: `app` imports `mind`, `mind` imports `interface`, and
   only the interface layer talks to `core`.

Most modules can be imported independently for manual experiments (`Server/interface/test_codes/`
contains several examples). When running in sandbox mode, replacements under `Server/sandbox/mocks`
implement the same interfaces so the rest of the stack keeps working.
