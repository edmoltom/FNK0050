import sys
import json
import asyncio
import base64
import websockets
import threading

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QTimer

SERVER_URI = "ws://192.168.1.135:8765" 

class StreamWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.image_label = QLabel("Waiting image...", self)
        self.image_label.setFixedSize(640, 480)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        self.setLayout(layout)

        self.ws = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)  # cada segundo

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(self.connect())
        self.async_loop = loop
        threading.Thread(target=loop.run_forever, daemon=True).start()

    async def connect(self):
        try:
            print("[StreamWidget] Connecting with server...")
            self.ws = await websockets.connect(SERVER_URI)
            print("[StreamWidget] Connected.")
        except Exception as e:
            print(f"[StreamWidget] Connection error: {e}")

    async def request_image(self):
        if not self.ws:
            return
        try:
            request = {"cmd": "capture", "args": {}}
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            if data.get("status") == "ok" and data.get("type") == "image":
                self.show_image_from_base64(data["data"])
        except Exception as e:
            print(f"[StreamWidget] Error receiving image: {e}")

    def tick(self):
        self.async_loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(self.request_image(), loop=self.async_loop)
        )

    def show_image_from_base64(self, base64_data):
        try:
            image_data = base64.b64decode(base64_data)
            image = QImage.fromData(image_data)
            pixmap = QPixmap.fromImage(image)
            self.image_label.setPixmap(pixmap)
        except Exception as e:
            print(f"[StreamWidget] Error showing image: {e}")