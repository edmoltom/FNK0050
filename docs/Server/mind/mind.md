# Mind Layer

*Part of the FNK0050 Lumo architecture.*

**Purpose:**  
The cognition stack that shapes persona, memory, and reasoning while delegating hardware mediation to the dedicated interface layer.

**Hierarchy:**  
app → mind → interface → core

**Updated:** 2025-10-10

The `Server/mind` package encapsulates the cognition stack that powers Lumo's reasoning and language capabilities. It sits above the physical `core/` layer, below the orchestration logic in `app/`, and collaborates with `interface/` components that execute hardware-facing actions.

## Architecture Overview

* **mind/context.py** defines the `MindContext`, a unified entry point that wires persona, language models, and memory for consumers such as the application runtime.
* **mind/llm_*** modules provide the LLM client, in-memory conversation state, speech hand-off helpers, and llama server lifecycle management.
* **mind/persona.py** implements persona construction and system prompts that give Lumo its identity.
* **Collaboration with `interface/`**: the mind layer now calls into `Server/interface/VoiceInterface.py`, `MovementControl.py`, `VisionManager.py`, and `LedController.py` to affect the body, ensuring cognition never touches hardware drivers directly.

## Flow Between Layers

1. **Core** exposes physical IO—microphones, speakers, LEDs, cameras—without any cognition attached.
2. **Interface** mediates between cognition and hardware, translating high-level intents coming from mind into actionable commands that respect hardware constraints.
3. **Mind** consumes those mediated capabilities to run perception-to-language loops, persisting short-term context and persona traits.
4. **App** orchestrates behaviours, instantiates `MindContext` during startup, and delegates conversation handling to mind-level components.

This separation keeps hardware concerns isolated in `core/`, mediation in `interface/`, reasoning and language in `mind/`, and coordination logic in `app/`, enabling modular experimentation and future distributed cognition deployments.

---
**See also:**
- [App Layer](../app/app.md)
- [Mind Layer](../mind/mind.md)
- [Interface Layer](../interface/interface.md)
- [Core Layer](../core/core.md)
