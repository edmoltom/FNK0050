from __future__ import annotations

import signal
import threading
import time
from types import FrameType
from typing import Any, Callable, Dict, Optional

from .builder import AppServices
from network.ws_server import start_ws_server


class AppRuntime:
    """Coordinate application services during execution."""

    def __init__(self, services: AppServices) -> None:
        self.svcs = services
        self._latest_detection: Dict[str, Any] = {}
        self._frame_handler: Optional[Callable[[Dict[str, Any] | None], None]] = None
        self._shutdown_event = threading.Event()
        self._running = False
        self._register_signal_handlers()

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

    def _register_signal_handlers(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, self._handle_shutdown_signal)
            except (ValueError, OSError, AttributeError):
                # Signal handlers can only be registered in the main thread and
                # may not exist on all platforms. In those scenarios we simply
                # keep the default behaviour.
                continue

    def _handle_shutdown_signal(self, signum: int, frame: Optional[FrameType]) -> None:
        self.stop()

        try:
            signal.default_int_handler(signum, frame)  # type: ignore[arg-type]
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            raise KeyboardInterrupt()

    def start(self) -> None:
        """Start the application services and, if enabled, the WS server.

        El apagado fino llegará en la segunda iteración; por ahora replicamos
        el comportamiento bloqueante del script original y confiamos en
        ``CTRL+C`` para detener la ejecución.
        """

        if self._running:
            return

        self._shutdown_event.clear()
        self._running = True

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
                try:
                    start_ws_server(vision, host=host, port=port)
                except KeyboardInterrupt:
                    pass
            elif vision_started:
                try:
                    while not self._shutdown_event.wait(timeout=1.0):
                        pass
                except KeyboardInterrupt:
                    pass
        finally:
            self.stop()

    def stop(self) -> None:
        if not self._running:
            self._shutdown_event.set()
        else:
            self._running = False
            self._shutdown_event.set()

        vision = self.svcs.vision if self.svcs.vision else None
        movement = self.svcs.movement if self.svcs.movement else None

        if vision and self.svcs.enable_vision:
            try:
                vision.stop()
            except Exception:
                pass

        if movement and self.svcs.enable_movement:
            try:
                movement.relax()
            finally:
                try:
                    movement.stop()
                except Exception:
                    pass

        # Hook reserved for the WebSocket wrapper implementation that will
        # arrive in the next iteration.
