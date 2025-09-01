import asyncio
import json
import threading
import websockets

SERVER_URI = "ws://192.168.1.133:8765"

class WebSocketClient:
    def __init__(self):
        self.uri = SERVER_URI
        self.websocket = None
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)
        self.connected = False
        self.lock = threading.Lock()
        self.receive_task = None
        self.thread.start()

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print("[WebSocketClient] Connected.")
        except Exception as e:
            print(f"[WebSocketClient] Connection failed: {e}")
            self.connected = False

    async def _send_command(self, command):
        if not self.connected:
            await self._connect()
        if not self.connected:
            return None
        try:
            await self.websocket.send(json.dumps(command))
            response = await self.websocket.recv()
            return json.loads(response)
        except Exception as e:
            print(f"[WebSocketClient] Error during send/receive: {e}")
            return None

    def send_command(self, command):
        future = asyncio.run_coroutine_threadsafe(self._send_command(command), self.loop)
        return future.result(timeout=5)

    async def _receive_stream(self, callback):
        try:
            async for message in self.websocket:
                try:
                    msg = json.loads(message)
                except Exception:
                    continue
                if msg.get("type") == "image":
                    callback(msg.get("frame"))
        except asyncio.CancelledError:
            pass

    async def _start_stream(self, callback):
        if not self.connected:
            await self._connect()
        if not self.connected:
            return
        await self.websocket.send(json.dumps({"cmd": "stream_start"}))
        self.receive_task = asyncio.create_task(self._receive_stream(callback))

    def start_stream(self, callback):
        asyncio.run_coroutine_threadsafe(self._start_stream(callback), self.loop)

    async def _stop_stream(self):
        if not self.connected or not self.websocket:
            return
        try:
            await self.websocket.send(json.dumps({"cmd": "stream_stop"}))
        except Exception:
            pass
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            self.receive_task = None

    def stop_stream(self):
        asyncio.run_coroutine_threadsafe(self._stop_stream(), self.loop)

    def close(self):
        if self.websocket:
            close_future = asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
            close_future.result(timeout=5)
        self.loop.call_soon_threadsafe(self.loop.stop)
