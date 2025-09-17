from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from .builder import AppServices
from network.ws_server import start_ws_server


class AppRuntime:
    """Coordinate application services during execution."""

    def __init__(self, services: AppServices) -> None:
        self.svcs = services
        self._latest_detection: Dict[str, Any] = {}
        self._frame_handler: Optional[Callable[[Dict[str, Any] | None], None]] = None

    @property
    def latest_detection(self) -> Dict[str, Any]:
        """Return a copy of the latest face detection."""
        return dict(self._latest_detection)

    @property
    def frame_handler(self) -> Optional[Callable[[Dict[str, Any] | None], None]]:
        return self._frame_handler

    def _store_latest_detection(self, result: Dict[str, Any] | None) -> None:
        self._latest_detection.clear()
        if result:
            self._latest_detection.update(result)

    def _register_frame_handler(self) -> None:
        prev_time = time.monotonic()

        def _handle(result: Dict[str, Any] | None) -> None:
            nonlocal prev_time
            now = time.monotonic()
            dt = now - prev_time
            prev_time = now

            if self.svcs.fsm:
                self.svcs.fsm.on_frame(result or {}, dt)

            self._store_latest_detection(result)

        self._frame_handler = _handle

    def start(self) -> None:
        """Start the application services and, if enabled, the WS server.

        El apagado fino llegará en la segunda iteración; por ahora replicamos
        el comportamiento bloqueante del script original y confiamos en
        ``CTRL+C`` para detener la ejecución.
        """

        vision = self.svcs.vision if self.svcs.vision else None
        movement = self.svcs.movement if self.svcs.movement else None

        if movement and self.svcs.enable_movement:
            movement.start()
            movement.relax()

        frame_handler = None
        if vision and self.svcs.enable_vision:
            self._register_frame_handler()
            frame_handler = self.frame_handler
            vision.set_frame_callback(frame_handler)

        vision_started = False

        try:
            if vision and self.svcs.enable_vision:
                vision.start(
                    interval_sec=float(self.svcs.interval_sec or 1.0),
                    frame_handler=frame_handler,
                )
                vision_started = True

            if self.svcs.enable_ws and vision:
                ws_cfg = self.svcs.ws_cfg or {}
                host = ws_cfg.get("host", "0.0.0.0")
                port = int(ws_cfg.get("port", 8765))
                start_ws_server(vision, host=host, port=port)
            elif vision_started:
                try:
                    while True:
                        time.sleep(1.0)
                except KeyboardInterrupt:
                    pass
        finally:
            if vision_started and vision:
                vision.stop()
