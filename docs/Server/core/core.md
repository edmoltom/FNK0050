# Core layer (`Server/core`)

*Part of the FNK0050 Lumo architecture.*

The core layer contains the hardware-oriented code that actually drives the robot: movement
controllers, vision pipelines, audio IO, and sensor utilities. Higher layers interact with these
modules exclusively through the interface facades so experiments can swap real devices for mocks.

## Contents overview

| Area | Location | Notes |
| ---- | -------- | ----- |
| Movement | `movement/` | Gait controller, servo drivers (PCA9685), calibration data, gesture player, and motion logging. |
| Vision | `vision/` | Camera abstraction, contour & face pipelines, dynamic thresholding helpers, overlays, and logging utilities. |
| Voice | `voice/` | Text-to-Speech implementation (Piper + SoX effects) and short sound effects. |
| Hearing | `hearing/` | Streaming Speech-to-Text using Vosk with pause/resume support. |
| LLM | `llm/` | HTTP client, llama.cpp process wrapper, conversation memory, persona definition, and helper scripts. |
| Sensing | `sensing/` | IMU access, odometry utilities, and supporting filters. |
| LEDs | `led/` | SPI LED strip driver and simple animation presets. |
| Shared libs | `../lib/` | Math helpers, filters, and device abstractions reused by core modules. |

## How the application uses it

1. `interface.MovementControl` instantiates the gait controller, exposes high-level commands, and is
   wrapped by `app.services.MovementService`.
2. `interface.VisionManager` builds on top of `core.vision` to capture frames and run the selected
   pipeline; results are consumed by the social FSM and optionally streamed over WebSocket.
3. `interface.VoiceInterface` composes `core.hearing`, `core.voice`, and `mind.llm` pieces to create
   a conversational loop.
4. `interface.sensor_controller` pulls data from `core.sensing` and feeds the `MindContext` via the
   `SensorGateway`.

Most modules can run on a Raspberry Pi with the Freenove hardware, but they also work with the
sandbox mocks for development on a desktop machine. Refer to the original Freenove documentation and
the scripts in `Server/demo/` or `Server/interface/test_codes/` for stand-alone examples.
