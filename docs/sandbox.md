# Lumo sandbox mode

The sandbox mode runs the entire server stack without touching real hardware. Sensors and actuators
are replaced with lightweight mocks that log their activity, making it ideal for development on a
laptop or CI environment.

## Goals

- Exercise the application runtime, social FSM, and conversation stack without a physical robot.
- Validate configuration changes quickly before deploying to the real hardware.
- Provide a safe environment for experimenting with new behaviours.

## Structure

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

Each mock mirrors the interface of the real service so the rest of the runtime does not notice the
difference.

| File | Emulates | Notes |
| ---- | -------- | ----- |
| `mock_vision.py` | Camera | Generates fake face detections and encoded frames. |
| `mock_movement.py` | Movement controller | Logs movement commands instead of driving servos. |
| `mock_voice.py` | Speech pipeline | Uses stdin/stdout to mimic STT/TTS interactions. |
| `mock_led.py` | LED controller | Prints LED state transitions. |

`sandbox_runtime.py` injects these mocks, builds `AppServices` in sandbox mode, and launches the
same `AppRuntime` used in production. The `SensorGateway` still feeds a real `BodyModel`, allowing
the mind to update proprioception.

## Running

```bash
python Server/sandbox/sandbox_runtime.py
```

You should see log output similar to:

```
[INFO] sandbox.mock_vision: [MOCK] Vision started
[INFO] sandbox.mock_voice: [YOU]: hola
[INFO] sandbox.mock_voice: [LUMO]: I heard: hola
[INFO] sandbox.mock_led: [MOCK-LED] state -> speaking
```

This indicates that the mind, social FSM, and mocks are wired correctly.

## Configuration

`sandbox_runtime.py` honours the same configuration file used by the real runtime. Keep `"mode":
"sandbox"` in `Server/app/app.json` (or the file you pass through `--config`) to select the mocks.
Other flags such as `enable_vision`, `enable_movement`, and `conversation.enable` behave exactly the
same as in real mode.

## Extending the sandbox

- Add additional mocks or scripted stimuli to simulate new sensors.
- Pipe mock outputs to a GUI or web dashboard for easier visualisation.
- Use the sandbox as the default environment for automated tests or CI pipelines.
