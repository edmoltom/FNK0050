import logging
import threading
import time

logger = logging.getLogger(__name__)


class SensorGateway:
    """Publishes sensor data directly to the Mind's BodyModel."""

    def __init__(self, controller, body_model, poll_rate_hz=10.0):
        self.controller = controller
        self.body = body_model
        self.poll_interval = 1.0 / poll_rate_hz
        self._thread = None
        self._running = False
        logger.info(f"[SENSOR] Gateway created (poll rate: {poll_rate_hz} Hz)")

    def _publish_packet(self, packet):
        if not isinstance(packet, dict):
            logger.debug("[SENSOR] Ignoring malformed packet: %s", packet)
            return

        sensor = packet.get("sensor")
        if not sensor:
            logger.debug("[SENSOR] Packet missing sensor identifier: %s", packet)
            return

        data = packet.get("data")
        confidence = packet.get("confidence", 1.0)
        kind = packet.get("type", "relative")
        self.body.correct_with_sensor(sensor, data, kind=kind, confidence=confidence)
        logger.debug(f"[SENSOR] BodyModel updated from {sensor}")

    def _loop(self):
        while self._running:
            try:
                imu_packet = self.controller.get_imu_packet()
                self._publish_packet(imu_packet)

                odom_packet = self.controller.get_odometry_packet()
                self._publish_packet(odom_packet)
            except Exception as e:  # pragma: no cover - defensive guard
                logger.warning(f"[SENSOR] Error while polling sensors: {e}")
            time.sleep(self.poll_interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="sensor-gateway",
            daemon=True,
        )
        self._thread.start()
        logger.info("[SENSOR] Gateway thread started")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("[SENSOR] Gateway stopped")
