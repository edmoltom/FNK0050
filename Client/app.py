"""Application entry points for client subsystems."""

from .gui.main_window import start_gui as _start_gui
from .network.ws_client import WebSocketClient


def start_gui():
    """Launch the graphical user interface."""
    _start_gui()


def start_network():
    """Initialise and return the WebSocket network client."""
    return WebSocketClient()


def start_all():
    """Start all available subsystems."""
    start_gui()
