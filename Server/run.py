import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

for folder in ["core", "lib", "test_codes", "network"]:
    folder_path = os.path.join(project_root, folder)
    if folder_path not in sys.path:
        sys.path.insert(0, folder_path)

from app.application import Application


def main() -> None:
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
