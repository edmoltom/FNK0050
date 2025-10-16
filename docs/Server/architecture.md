# Lumo System Architecture

*Part of the FNK0050 project.*

**Updated:** 2025-10-10  
**Hierarchy:** app → mind → interface → core

## Overview

Lumo is a modular robotic–cognitive platform designed for experimentation in perception, interaction, and self-awareness.  
The architecture is layered to separate cognition, behavior orchestration, and hardware access.  
Each layer is self-contained yet interoperable, allowing simulations without physical hardware.

## Layered Model

### 1. App Layer (`Server/app`)
- **Role:** Orchestrates high-level behavior, finite-state machines, and coordination between cognitive services.  
- **Analogy:** Executive cortex – plans and prioritizes.  
- **Key Components:** `BehaviorManager`, `SocialFSM`, `AppRuntime`.  
- **Dependencies:** Uses `mind/` for cognition and `interface/` for external actions.

### 2. Mind Layer (`Server/mind`)
- **Role:** Holds reasoning, language, memory, and persona.  
- **Analogy:** Cognitive cortex – where “thought” happens.  
- **Key Components:** `MindContext`, `persona.py`, `llm_client`, `proprioception/BodyModel`.  
- **Interaction:** Sends intents to `interface/` (voice, vision, motion) and receives sensory feedback.  
- **Goal:** Keep cognition pure, detached from physical hardware.

### 3. Interface Layer (`Server/interface`)
- **Role:** Bridge between cognition and the physical world.  
- **Analogy:** Peripheral nervous system – translates abstract commands into physical actions.  
- **Modules:** `MovementControl`, `VisionManager`, `VoiceInterface`, `LedController`.  
- **Responsibilities:**  
  1. Translate high-level intents from `mind/` into safe, hardware-aware commands.  
  2. Normalize sensory data before it reaches `mind/`.  
  3. Preserve the one-way dependency flow: `app → mind → interface → core`.

### 4. Core Layer (`Server/core`)
- **Role:** Implements hardware drivers and low-level control.  
- **Analogy:** Body and sensors – where electricity meets reality.  
- **Modules:** `movement/`, `vision/`, `voice/`, `hearing/`, `sensing/`, `led/`, `llm/`.  
- **Dependencies:** Exposed only through `interface/`; higher layers never import `core` directly.

## Data Flow Summary



User → App (behavior control)
↓
Mind (reasoning & decisions)
↓
Interface (translation & mediation)
↓
Core (hardware execution)


Each arrow represents a boundary where data changes form:
- Commands become physical actions.
- Sensory data becomes structured perception.
- Context and confidence values propagate upward.

## Design Principles

1. **Layer Isolation** – Each layer knows only the one below it.  
2. **Replaceability** – Any layer can be simulated or swapped.  
3. **Transparency** – Logging at each boundary for observability.  
4. **Scalability** – Future components (navigation, emotions, sandbox) can plug in without breaking contracts.

## Future Extensions

- **Sandbox Mode:** A virtual environment allowing the mind and interface to operate without hardware.  
- **Navigation Layer:** Integration of spatial reasoning and SLAM for autonomous movement.  
- **Emotion Engine:** Adds affective states influencing behavior and LED feedback.  
- **Distributed Mind:** Running the cognitive layer remotely while maintaining real-time physical control.

---
**See also:**
- [App Layer](app/app.md)
- [Mind Layer](mind/mind.md)
- [Interface Layer](interface/interface.md)
- [Core Layer](core/core.md)
