from __future__ import annotations

import asyncio
import logging
import signal
import threading
import time
from types import FrameType
from typing import Any, Callable, Dict, Optional

from .builder import AppServices
from network import ws_server


logger = logging.getLogger(__name__)


class AppRuntime:
    """Coordinate application services during execution."""

    def __init__(self, services: AppServices) -> None:
        self.svcs = services
        self._latest_detection: Dict[str, Any] = {}
        self._frame_handler: Optional[Callable[[Dict[str, Any] | None], None]] = None
        self._shutdown_event = threading.Event()
        self._running = False
        self._stop_lock = threading.Lock()
        self._stop_completed = False
        self._ws_thread: Optional[threading.Thread] = None
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
        with self._stop_lock:
            self._stop_completed = False
        self._running = True

        vision = self.svcs.vision if self.svcs.vision else None
        movement = self.svcs.movement if self.svcs.movement else None
        conversation = self.svcs.conversation if self.svcs.conversation else None

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

            if conversation and self.svcs.enable_conversation:
                try:
                    logger.info("AppRuntime: starting conversation service")
                    conversation.start()
                    logger.info("AppRuntime: conversation service started")
                except Exception:
                    logger.exception(
                        "AppRuntime: error while starting conversation service"
                    )
                    raise

            if self.svcs.enable_ws and vision:
                ws_cfg = self.svcs.ws_cfg or {}
                host = ws_cfg.get("host", "0.0.0.0")
                port = int(ws_cfg.get("port", 8765))
                self._start_ws_server(vision, host=host, port=port)
                try:
                    while not self._shutdown_event.wait(timeout=0.5):
                        pass
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
        vision = self.svcs.vision if self.svcs.vision else None
        movement = self.svcs.movement if self.svcs.movement else None
        conversation = self.svcs.conversation if self.svcs.conversation else None

        self._shutdown_event.set()

        with self._stop_lock:
            if self._stop_completed:
                return
            self._stop_completed = True
            self._running = False

        if conversation and self.svcs.enable_conversation:
            try:
                logger.info("AppRuntime: stopping conversation service")
                conversation.stop(terminate_process=True, shutdown_resources=True)
                logger.info("AppRuntime: conversation service stopped")
            except Exception:
                logger.exception(
                    "AppRuntime: error while stopping conversation service"
                )
                pass

            try:
                conversation.join()
            except Exception:
                pass

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

        ws_thread = self._ws_thread
        if ws_thread and ws_thread.is_alive():
            ws_thread.join(timeout=1.0)
        self._ws_thread = None

    def _start_ws_server(self, vision: Any, *, host: str, port: int) -> None:
        if self._ws_thread and self._ws_thread.is_alive():
            return

        def _run() -> None:
            asyncio.run(self._run_ws_server(vision, host=host, port=port))

        thread = threading.Thread(target=_run, name="ws-server", daemon=True)
        self._ws_thread = thread
        thread.start()

    async def _run_ws_server(self, vision: Any, *, host: str, port: int) -> None:
        handler = ws_server.make_handler(vision)
        try:
            import websockets
        except Exception:  # pragma: no cover - library import failure
            return

        addr = ws_server._get_local_ip() if hasattr(ws_server, "_get_local_ip") else host
        print(f"WebSocket listening at ws://{addr}:{port} ...")

        async with websockets.serve(handler, host, port):
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, self._shutdown_event.wait)
            finally:
                await self._cancel_pending_tasks()

    async def _cancel_pending_tasks(self) -> None:
        loop = asyncio.get_running_loop()
        pending = [task for task in asyncio.all_tasks(loop=loop) if not task.done()]
        for task in pending:
            if task is asyncio.current_task(loop=loop):
                continue
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
