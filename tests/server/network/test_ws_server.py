from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Server"))
sys.path.insert(0, str(ROOT))

from network.ws_server import start_ws_server
from app.application import Application
from app.controllers.robot_controller import RobotController


def main():
    print("Starting WebSocket server...")
    app = Application()
    controller = RobotController(app.movement_service, app.vision_service)
    start_ws_server(app, controller)


if __name__ == "__main__":
    main()

