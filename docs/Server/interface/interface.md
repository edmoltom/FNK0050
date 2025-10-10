# Interface Layer

*Part of the FNK0050 Lumo architecture.*

**Purpose:**  
Bridge cognition and hardware by mediating between mind-level intentions and the core subsystems that drive motion, vision, and voice.

**Hierarchy:**  
app → mind → interface → core

**Updated:** 2025-10-10

The `Server/interface` package hosts the façade classes that connect Lumo's cognitive services to the physical world. It ensures that data and commands always flow outward from the application runtime through `mind/` into `interface/`, finally reaching the low-level drivers in `core/`.

## Modules

* **MovementControl.py** – Coordinates locomotion requests from the mind layer, translating them into `core/movement` commands while applying safety guards and smoothing.
* **VisionManager.py** – Manages camera streaming and detection pipelines, exposing snapshots and telemetry to mind and app consumers without leaking hardware details.
* **VoiceInterface.py** – Orchestrates the speech pipeline by combining speech-to-text, LLM querying, and text-to-speech while synchronising LED feedback.
* **LedController.py** – Provides asynchronous LED animations triggered by higher layers, delegating raw SPI access to `core/led`.

## Role in the Architecture

The interface layer mediates between cognition and hardware, ensuring that:

1. High-level intents from `mind/` are translated into safe, hardware-aware commands.
2. Sensor data from `core/` is normalised before reaching cognitive components.
3. The dependency chain remains one-directional: **app → mind → interface → core**.
4. Modules such as `LedController`, `MovementControl`, `VisionManager`, and `VoiceInterface` remain cohesive entry points for the higher layers, consolidating asynchronous loops and resource management in one place.

By centralising these façades, the interface layer makes it straightforward to swap or mock hardware drivers and keeps `mind/` focused purely on reasoning logic.

---
**See also:**
- [App Layer](../app/app.md)
- [Mind Layer](../mind/mind.md)
- [Interface Layer](../interface/interface.md)
- [Core Layer](../core/core.md)
