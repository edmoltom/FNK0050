import os
import json
import websockets


class WebSocketClient:
    """Simple asynchronous WebSocket client.

    The server URI can be provided either as a constructor argument or
    through the ``SERVER_URI`` environment variable.  If neither is
    supplied, ``ws://192.168.1.133:8765`` is used as a fallback.

    The client exposes :func:`connect`, :func:`send_command` and
    :func:`close` coroutines and implements the asynchronous context
    manager protocol so it can be used with ``async with``.
    """

    DEFAULT_URI = "ws://192.168.1.133:8765"

    def __init__(self, uri: str | None = None):
        # Environment variable takes precedence over the hard coded default
        env_uri = os.getenv("SERVER_URI")
        self.uri = uri or env_uri or self.DEFAULT_URI
        self.websocket = None
        self.connected = False

    async def connect(self):
        """Establish a websocket connection to ``self.uri``."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print("[WebSocketClient] Connected.")
        except Exception as e:  # pragma: no cover - defensive branch
            print(f"[WebSocketClient] Connection failed: {e}")
            self.connected = False

    async def send_command(self, command):
        """Send ``command`` and wait for the server response."""
        if not self.connected:
            await self.connect()
        if not self.connected:  # connection failed
            return None
        try:
            await self.websocket.send(json.dumps(command))
            response = await self.websocket.recv()
            return json.loads(response)
        except Exception as e:  # pragma: no cover - defensive branch
            print(f"[WebSocketClient] Error during send/receive: {e}")
            return None

    async def close(self):
        """Close the websocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.connected = False

    # ------------------------------------------------------------------
    # Async context manager protocol
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

