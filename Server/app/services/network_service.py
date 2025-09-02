from __future__ import annotations

"""Service to expose robot functionality over a WebSocket server."""

import asyncio
import logging
import threading
from typing import TYPE_CHECKING

from ...network.ws_server import start_ws_server_async
from ..controllers.robot_controller import RobotController

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from ..application import Application


class NetworkService:
    """Thin wrapper that runs the WebSocket server in the background."""

    def __init__(self, app: "Application", *, enable_logging: bool = False) -> None:
        self._app = app
        self._controller = RobotController(app.movement_service, app.vision_service)
        self._log = logging.getLogger(__name__) if enable_logging else None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the websocket server in a background thread."""
        if self._loop is not None:
            return
        if self._log:
            self._log.debug("Starting network service")

        self._loop = asyncio.new_event_loop()
        self._task = self._loop.create_task(
            start_ws_server_async(self._app, self._controller)
        )

        def _run() -> None:
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_forever()
            finally:
                self._loop.close()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def update(self) -> None:  # pragma: no cover - no periodic work yet
        return None

    def stop(self) -> None:
        """Stop the websocket server."""
        if self._loop and self._task:
            if self._log:
                self._log.debug("Stopping network service")
            self._loop.call_soon_threadsafe(self._task.cancel)
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread:
                self._thread.join(timeout=0.1)
        self._loop = None
        self._thread = None
        self._task = None

