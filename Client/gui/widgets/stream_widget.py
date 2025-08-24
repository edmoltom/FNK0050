import base64
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from gui.services.stream_service import StreamService

class StreamWidget(QWidget):
    def __init__(self, stream_service: StreamService):
        super().__init__()
        self.setWindowTitle("Robot Camera Stream")
        self.layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.image_label)
        self.setLayout(self.layout)

        # High-level service used to fetch frames.  This indirection allows
        # easy injection of fake services for tests.
        self.service = stream_service
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_image)
        self.timer.start(1000)  # fetch every second

    def update_image(self):
        self.fetch_and_display()

    def fetch_and_display(self):
        image_data = self.service.fetch_image()
        if image_data:
            pixmap = self.base64_to_pixmap(image_data)
            self.image_label.setPixmap(pixmap)

    def base64_to_pixmap(self, base64_str):
        img_bytes = base64.b64decode(base64_str)
        img = QImage.fromData(img_bytes)
        return QPixmap.fromImage(img)