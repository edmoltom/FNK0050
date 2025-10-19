# FNK0050 – Lumo Robot Playground

Lumo is a personal sandbox built on top of the Freenove Robot Dog Kit for Raspberry Pi. The
repository mixes the original vendor code with a growing set of experiments around computer
vision, speech, proprioception, and language-enabled interaction. The goal is to iterate on
ideas quickly while keeping the codebase hackable from a laptop or directly on the robot.

![Icono del proyecto](docs/icon.png)

## Repository layout

| Path | Purpose |
| ---- | ------- |
| `Server/` | Main runtime for the robot and the sandbox mocks. Holds the cognition stack, hardware facades, and orchestration code. |
| `Client/` | Desktop utilities for monitoring or manually driving the robot. |
| `docs/` | Architecture notes, how-to guides, and internal references. |
| `Tools/` | Helper scripts used during development (calibration, profiling, etc.). |

## Running the server

The runtime boots from `Server/run.py`. Use the default configuration or provide your own JSON
file describing which services to enable.

```bash
python Server/run.py --config Server/app/app.json
```

Key switches in `Server/app/app.json`:

- `mode`: `"sandbox"` uses mock sensors/actuators, `"real"` talks to the hardware.
- `enable_vision`, `enable_movement`, `enable_ws`, `enable_conversation`: toggle services on/off.
- `vision`: camera mode (`object`/`face`), FPS limits, and Haar profile settings.
- `conversation`: llama.cpp binary/model, health-check tuning, and concurrency limits.

When conversation is enabled the runtime auto-starts `llama-server`, wires Speech-to-Text/Voice
interfaces, and exposes a WebSocket stream with camera frames if requested.

## Running the sandbox

The sandbox mimics the robot without touching real hardware. It is ideal for smoke tests or when
working remotely.

```bash
python Server/sandbox/sandbox_runtime.py
```

The script replaces hardware drivers with mocks, keeps the same runtime wiring, and streams sensor
data into the mind’s `BodyModel` so behaviour can be exercised end-to-end.

## Tests

Server tests run with `pytest` and cover the application runtime, WebSocket helpers, and
conversation pipeline contracts.

```bash
pytest Server/tests
```

Most tests rely on mocks and can run without camera/audio hardware. Disable the conversation flag
in your config if you are running them on a constrained environment.

## Logging

Runtime logs rotate to `robot.log` in the project root. See [docs/logging.md](docs/logging.md)
for details on monitoring and rotation policy.

## Documentation

- [docs/Server/architecture.md](docs/Server/architecture.md) – system overview.
- [docs/conversation.md](docs/conversation.md) – enabling the conversation stack.
- [docs/sandbox.md](docs/sandbox.md) – how the sandbox wiring works.

The documentation is evolving together with the codebase; feel free to extend it as new modules or
behaviours appear.
