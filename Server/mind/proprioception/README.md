# Proprioception Module

This directory implements Lumo’s internal body awareness system.

## Components

- **BodyModel**: Tracks Lumo’s internal pose `(x, y, θ, v, w, confidence)`.
- **SensorBus**: Mediates sensory data from the physical layer (`core/sensing`)
  and updates the BodyModel accordingly.

## Typical Flow

1. A sensor in `core/sensing` sends a packet:
   ```python
   packet = {
       "sensor": "odometry",
       "type": "relative",
       "data": {"dx": 0.02, "dy": 0.0, "dtheta": 0.01},
       "confidence": 0.95
   }
   ```
   The application calls:

   ```python
   mind.sensor_bus.receive(packet)
   ```

   The SensorBus routes the update to BodyModel, adjusting the internal pose and confidence.

## Future Extensions

- Sensor fusion (Kalman / Complementary filters)
- Environment mapping
- Simulation and sandbox testing
