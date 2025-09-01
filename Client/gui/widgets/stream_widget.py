import base64
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

class StreamWidget(QWidget):
    def __init__(self, ws_client):
        super().__init__()
        self.setWindowTitle("Robot Vision Stream")
        self.layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.image_label)
        self.setLayout(self.layout)

        self.client = ws_client
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_image)
        self.timer.start(1000)  # fetch every second

    def update_image(self):
        self.fetch_and_display()

    def fetch_and_display(self):
        response = self.client.send_command({"cmd": "capture"})
        if response and response.get("status") == "ok":
            image_data = response.get("data")
            if image_data:
                pixmap = self.base64_to_pixmap(image_data)
                self.image_label.setPixmap(pixmap)

    def base64_to_pixmap(self, base64_str):
        img_bytes = base64.b64decode(base64_str)
        img = QImage.fromData(img_bytes)
        return QPixmap.fromImage(img)
