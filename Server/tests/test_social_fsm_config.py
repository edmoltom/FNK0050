from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[2]
# Make Server packages available
sys.path.append(str(ROOT / "Server"))
sys.path.append(str(ROOT / "Server/lib"))

# Stub out heavy dependencies used by SocialFSM imports
core_mod = types.ModuleType("core")


class MovementControl:
    head_limits = (0.0, 0.0, 0.0)

    def stop(self):
        pass

    def head_deg(self, deg, duration_ms=0):
        pass


class VisionManager:
    pass


core_mod.MovementControl = MovementControl
core_mod.VisionManager = VisionManager
sys.modules["core"] = core_mod
sys.modules["core.MovementControl"] = core_mod
sys.modules["core.VisionManager"] = core_mod

control_mod = types.ModuleType("control")
pid_mod = types.ModuleType("control.pid")


class Incremental_PID:
    def __init__(self, *_, **__):
        pass

    def PID_compute(self, error):
        return 0.0


pid_mod.Incremental_PID = Incremental_PID
control_mod.pid = pid_mod
sys.modules["control"] = control_mod
sys.modules["control.pid"] = pid_mod

services_pkg = types.ModuleType("app.services")
sys.modules["app.services"] = services_pkg

movement_service_mod = types.ModuleType("app.services.movement_service")


class MovementService:
    def __init__(self):
        self.mc = MovementControl()

    def stop(self):
        pass


movement_service_mod.MovementService = MovementService
sys.modules["app.services.movement_service"] = movement_service_mod

vision_service_mod = types.ModuleType("app.services.vision_service")


class VisionService:
    def __init__(self):
        self.vm = VisionManager()


vision_service_mod.VisionService = VisionService
sys.modules["app.services.vision_service"] = vision_service_mod

from app.controllers.social_fsm import SocialFSM


def test_config_values_override_defaults():
    cfg = {
        "behavior": {
            "social_fsm": {
                "deadband_x": 0.5,
                "lock_frames_needed": 10,
                "miss_release": 7,
                "interact_ms": 2000,
            }
        }
    }
    fsm = SocialFSM(VisionService(), MovementService(), cfg)
    assert fsm.deadband_x == 0.5
    assert fsm.lock_frames_needed == 10
    assert fsm.miss_release == 7
    assert fsm.interact_ms == 2000

