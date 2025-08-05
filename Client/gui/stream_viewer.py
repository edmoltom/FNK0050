import sys
import asyncio
import base64
import json
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QTimer
from PIL import Image
from io import BytesIO
import websockets

SERVER_URI = "ws://192.168.1.135:8765" 


class ImageStreamViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cat-bot Viewer 🐾")
        self.setGeometry(100, 100, 640, 480)

        # QLabel to display the image
        self.image_label = QLabel("Connecting...", self)
        self.image_label.setFixedSize(640, 480)

        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Timer to request image every 1000 ms
        self.timer = QTimer()
        self.timer.timeout.connect(self.request_image)
        self.timer.start(1000)

        # Initialize WebSocket
        self.ws = None
        asyncio.get_event_loop().run_until_complete(self.connect())

    async def connect(self):
        try:
            self.ws = await websockets.connect(SERVER_URI)
            print("Connected to the WebSocket server.")
        except Exception as e:
            print(f"Connection error: {e}")
            self.image_label.setText("Connection error")

    def request_image(self):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(self.send_and_receive())
        else:
            loop.run_until_complete(self.send_and_receive())

    async def send_and_receive(self):
        if self.ws:
            try:
                msg = json.dumps({"cmd": "capture", "args": {}})
                await self.ws.send(msg)
                response = await self.ws.recv()
                data = json.loads(response)
                if data["status"] == "ok" and data["type"] == "image":
                    self.show_image_from_base64(data["data"])
            except Exception as e:
                print(f"Communication error: {e}")
                self.image_label.setText("Communication error")

    def show_image_from_base64(self, base64_str):
        image_data = base64.b64decode(base64_str)
        pil_image = Image.open(BytesIO(image_data))
        rgb_image = pil_image.convert("RGB")
        w, h = rgb_image.size
        qt_image = QImage(rgb_image.tobytes(), w, h, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.image_label.setPixmap(pixmap)


def start_stream_viewer():
    app = QApplication(sys.argv)
    viewer = ImageStreamViewer()
    viewer.show()
    sys.exit(app.exec())