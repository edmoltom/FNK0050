import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from gui.widgets.stream_widget import StreamWidget

class ImageStreamViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Viewer")
        self.resize(800, 600)

        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(StreamWidget())
        widget.setLayout(layout)

        self.setCentralWidget(widget)

def start_gui():
    app = QApplication(sys.argv)
    window = ImageStreamViewer()
    window.show()
    sys.exit(app.exec())