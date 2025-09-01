from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3] / "Client"
sys.path.insert(0, str(ROOT))

from gui.main_window import start_gui


def main():
    print("Starting StreamViewer...")
    start_gui()


if __name__ == "__main__":
    main()

