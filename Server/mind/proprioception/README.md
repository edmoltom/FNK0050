# Proprioception Subsystem

Lumo's proprioception subsystem models the robot's spatial self-awareness. It
fuses predictions from odometry with observations from physical sensors to
maintain an internal estimate of the body pose. The resulting body model is
accessible from the broader mind stack, enabling cognitive components to reason
about movement, balance, and situational context.

## Interfaces

- **Sensor inputs** — Future components will connect to `core.sensing` to ingest
  odometry, ultrasonic, and IMU data streams.
- **Mind integrations** — `MindContext` and `BehaviorManager` will use the body
  model to ground reasoning and decision making in the robot's physical state.

## Roadmap

The initial `BodyModel` class provides the storage and summary scaffolding for
Lumo's internal pose. Upcoming work will add:

- Sensor fusion algorithms that blend odometry with distance and inertial
  corrections.
- Confidence estimation to quantify localization certainty.
- Deeper integration with behavior and motivation systems so actions can adapt
  to the robot's perceived body dynamics.
