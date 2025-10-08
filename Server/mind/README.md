# Mind Layer

The `mind/` package encapsulates the cognition stack that powers Lumo's
reasoning and language capabilities. It sits above the physical `core/` layer
and below the orchestration logic in `app/`, exposing a clean boundary for
thought processes, memory, and persona modelling.

## Architecture Overview

* **mind/context.py** defines the `MindContext`, a unified entry point that
  wires persona, language models, and memory for consumers such as the
  application runtime.
* **mind/interface/** contains bridges that connect cognitive services to the
  body, for example the voice interface that coordinates speech, hearing, and
  LEDs.
* **mind/llm_\*** modules provide the LLM client, in-memory conversation state,
  speech hand-off helpers, and llama server lifecycle management.
* **mind/persona.py** implements persona construction and system prompts that
  give Lumo its identity.

## Flow Between Layers

1. **Core** exposes physical IO—microphones, speakers, LEDs, cameras—without
   any cognition attached.
2. **Mind** consumes those hardware interfaces to run perception-to-language
   loops, persisting short-term context and persona traits.
3. **App** orchestrates behaviours, instantiates `MindContext` during startup,
   and delegates conversation handling to mind-level components.

This separation keeps hardware concerns isolated in `core/`, reasoning and
language in `mind/`, and coordination logic in `app/`, enabling modular
experimentation and future distributed cognition deployments.
