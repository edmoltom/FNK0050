# Proprioception Module

This directory implements Lumo’s internal body awareness system.

## Components

- **BodyModel**: Tracks Lumo’s internal pose `(x, y, θ, v, w, confidence)`.

## Typical Flow

1. The `SensorController` polls hardware drivers and delivers packets to
   `SensorGateway`.
2. `SensorGateway` calls `BodyModel.correct_with_sensor(...)`, fusing
   corrections immediately.
3. Higher-level cognitive modules query the updated `BodyModel` state via
   `MindContext`.

## Future Extensions

- Sensor fusion (Kalman / Complementary filters)
- Environment mapping
- Simulation and sandbox testing
