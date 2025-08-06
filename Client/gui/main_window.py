import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from gui.widgets.stream_widget import StreamWidget
from network.ws_client import WebSocketClient

SERVER_URI = "ws://192.168.1.135:8765"

class ImageStreamViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Viewer")
        self.resize(800, 600)

        self.ws_client = WebSocketClient(SERVER_URI)

        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(StreamWidget(self.ws_client))
        widget.setLayout(layout)

        self.setCentralWidget(widget)

def start_gui():
    app = QApplication(sys.argv)
    window = ImageStreamViewer()
    window.show()
    sys.exit(app.exec())