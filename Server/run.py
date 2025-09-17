from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

for relative_path in ("app", "core", "lib", "network", "test_codes"):
    folder_path = PROJECT_ROOT / relative_path
    if folder_path.exists():
        folder_path_str = str(folder_path)
        if folder_path_str not in sys.path:
            sys.path.insert(0, folder_path_str)

#from hello_world import main
#from test_led_controller import main
#from test_led import main
#from test_gamepad import main
#from test_visual_perception import main
#from test_llm_tts import main
#from test_voice_loop import main
#from test_voice_interface import main
from app.application import main


if __name__ == "__main__":
    main()
