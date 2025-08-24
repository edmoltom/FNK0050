import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from gui.widgets.stream_widget import StreamWidget
from gui.services.stream_service import StreamService
from network.ws_client import WebSocketClient

class ImageStreamViewer(QMainWindow):
    def __init__(self, stream_service: StreamService | None = None):
        super().__init__()
        self.setWindowTitle("Robot Viewer")
        self.resize(800, 600)

        # Allow the caller to provide a custom service (e.g. a mock for tests).
        self.stream_service = stream_service or StreamService(WebSocketClient())

        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(StreamWidget(self.stream_service))
        widget.setLayout(layout)

        self.setCentralWidget(widget)

def start_gui():
    app = QApplication(sys.argv)
    window = ImageStreamViewer()
    window.show()
    sys.exit(app.exec())