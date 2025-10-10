import time
import logging

logger = logging.getLogger(__name__)


class SensorBus:
    """
    Mediates all incoming sensor data between the physical layer (core/sensing)
    and the cognitive layer (mind/proprioception).
    Responsible for normalizing packets, routing updates to BodyModel,
    and maintaining minimal state per sensor.
    """

    def __init__(self, body_model):
        self.body_model = body_model
        self.last_data = {}
        self.last_timestamp = {}
        self.subscribers = []  # optional callbacks for events or monitoring

    def receive(self, packet: dict):
        """
        Main entry point for any sensor packet.
        Packet format:
            {
              "sensor": str,
              "timestamp": float,
              "type": "relative" | "absolute" | "environmental",
              "data": dict,
              "confidence": float (optional)
            }
        """
        if not isinstance(packet, dict):
            logger.warning("[SENSORBUS] Invalid packet: not a dict")
            return

        sensor = packet.get("sensor", "unknown")
        stype = packet.get("type", "unknown")
        data = packet.get("data", {})
        conf = float(packet.get("confidence", 1.0))
        ts = packet.get("timestamp", time.time())

        self.last_data[sensor] = data
        self.last_timestamp[sensor] = ts

        if stype == "relative" and {"dx", "dy", "dtheta"} <= data.keys():
            self._handle_odometry(sensor, data, conf)
        elif stype == "absolute":
            self._handle_absolute(sensor, data, conf)
        elif stype == "environmental":
            self._handle_environment(sensor, data, conf)
        else:
            logger.debug("[SENSORBUS] Unrecognized type or incomplete data: %s", stype)

        self._notify_subscribers(packet)

    def _handle_odometry(self, sensor, data, conf):
        dx, dy, dtheta = data["dx"], data["dy"], data["dtheta"]
        self.body_model.update_odometry(dx, dy, dtheta)
        self._adjust_confidence(conf)
        logger.debug("[SENSORBUS] [%s] Δx=%.3f Δy=%.3f Δθ=%.3f (conf=%.2f)",
                     sensor, dx, dy, dtheta, conf)

    def _handle_absolute(self, sensor, data, conf):
        try:
            self.body_model.correct_with_sensor(data)
            self._adjust_confidence(conf)
            logger.debug("[SENSORBUS] [%s] absolute correction %s (conf=%.2f)",
                         sensor, data, conf)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("[SENSORBUS] Correction failed from %s: %s", sensor, e)

    def _handle_environment(self, sensor, data, conf):
        logger.debug(
            "[SENSORBUS] [%s] environmental data: %s (conf=%.2f)",
            sensor,
            data,
            conf,
        )

    def _adjust_confidence(self, conf):
        alpha = 0.2
        self.body_model.confidence = (
            (1 - alpha) * self.body_model.confidence + alpha * conf
        )

    def _notify_subscribers(self, packet):
        for callback in self.subscribers:
            try:
                callback(packet)
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("[SENSORBUS] Subscriber callback failed: %s", e)

    def register_subscriber(self, callback):
        """Allow other systems (e.g., BehaviorManager) to receive notifications."""
        self.subscribers.append(callback)
