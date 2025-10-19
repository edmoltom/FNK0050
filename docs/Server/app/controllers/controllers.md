# Controllers (`Server/app/controllers`)

The controllers package provides import shortcuts to the components that coordinate perception and
movement. The actual implementations live in the mind and interface layers, but exposing them from
`app.controllers` keeps legacy scripts working.

## Available controllers

| Symbol | Source | Purpose |
| ------ | ------ | ------- |
| `FaceTracker` | `mind.perception.face_tracker.FaceTracker` | Tracks faces detected by the vision pipeline and commands head/body adjustments through `MovementControl`. |
| `SocialFSM` | `mind.behavior.social_fsm.SocialFSM` | Finite state machine that pauses/alines/interacts based on face detections and timing heuristics. |
| `AxisXTurnController`, `AxisYHeadController`, `VisualTracker` | `interface.tracker.visual_tracker` | Low-level helpers used by the face tracker to move the robot smoothly. |

The module re-exports these symbols lazily so importing `app.controllers.FaceTracker` resolves to the
latest implementation without creating additional dependencies at import time.

## `SocialFSM` at a glance

`SocialFSM` consumes face detections produced by `VisionService` and decides how the robot should
behave:

- **States**: `IDLE`, `ALIGNING`, `INTERACT`.
- **Transitions**: the FSM aligns the body until the face is centred, keeps interacting while the
  lock is maintained, and falls back to idle once detections disappear.
- **Behaviour hooks**: optional callbacks allow the application layer to start or stop the
  `ConversationService` when interaction begins or ends.
- **Utilities**: `pause()` freezes the FSM (used while speaking), `resume()` restarts updates, and
  `mute_social(True)` keeps tracking active but disables sound effects.

Configuration lives in `app.json` under `behavior.social_fsm` (deadband, lock frames, cooldowns,
interaction duration). The builder passes those values when constructing the FSM.

