import base64
from PyQt6.QtCore import Qt
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
        self.client.start_stream(self.on_frame)

    def on_frame(self, base64_image):
        pixmap = self.base64_to_pixmap(base64_image)
        self.image_label.setPixmap(pixmap)

    def base64_to_pixmap(self, base64_str):
        img_bytes = base64.b64decode(base64_str)
        img = QImage.fromData(img_bytes)
        return QPixmap.fromImage(img)

    def closeEvent(self, event):
        self.client.stop_stream()
        super().closeEvent(event)
