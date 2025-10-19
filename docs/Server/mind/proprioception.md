# Mind proprioception

Proprioception gives the mind a sense of the robot’s pose and motion. The pipeline is intentionally
simple so it can operate with either real sensors or sandbox mocks.

## Data flow

1. `interface.sensor_controller.SensorController` polls the IMU and odometry modules from
   `core.sensing`.
2. `interface.sensor_gateway.SensorGateway` runs in a background thread, forwarding each packet to
   the mind at a configurable rate (default: 10 Hz).
3. `mind.proprioception.body_model.BodyModel` fuses the incoming data, updating position, heading,
   and a confidence score.

There is no intermediate bus layer; packets go straight from the gateway into the body model, which
keeps the implementation easy to reason about and trivial to mock.

## Extending proprioception

- Implement additional `get_*_packet()` methods in `SensorController` to expose new sensors. Packets
  are dictionaries containing `sensor`, `timestamp`, `type`, `data`, and an optional `confidence`.
- Call `SensorGateway._publish_packet()` with the new packet; the gateway ignores malformed data
  gracefully.
- Extend `BodyModel.correct_with_sensor()` to support the new sensor type.

Use `MindContext.body.summary()` to inspect the fused state during runtime or tests.
