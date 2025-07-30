import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))

for folder in ['core', 'lib', 'app']:
    folder_path = os.path.join(project_root, folder)
    if folder_path not in sys.path:
        sys.path.insert(0, folder_path)

#from hello_world import main
from test_gamepad import main  

if __name__ == '__main__':
    main()