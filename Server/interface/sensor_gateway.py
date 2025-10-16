import threading
import time
import logging

logger = logging.getLogger(__name__)


class SensorGateway:
    """Background publisher of sensor data to the Mind's SensorBus."""

    def __init__(self, controller, sensor_bus, poll_rate_hz=10.0):
        self.controller = controller
        self.sensor_bus = sensor_bus
        self.poll_interval = 1.0 / poll_rate_hz
        self._thread = None
        self._running = False
        logger.info(f"[SENSORBUS] Gateway created (poll rate: {poll_rate_hz} Hz)")

    def _loop(self):
        while self._running:
            try:
                imu_packet = self.controller.get_imu_packet()
                self.sensor_bus.receive(imu_packet)

                odom_packet = self.controller.get_odometry_packet()
                self.sensor_bus.receive(odom_packet)
            except Exception as e:
                logger.warning(f"[SENSORBUS] Error while polling sensors: {e}")
            time.sleep(self.poll_interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="sensor-gateway", daemon=True)
        self._thread.start()
        logger.info("[SENSORBUS] Gateway thread started")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("[SENSORBUS] Gateway stopped")
