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

voice_mod = types.ModuleType("core.voice")
sfx_mod = types.ModuleType("core.voice.sfx")


def play_sound(_):
    pass


sfx_mod.play_sound = play_sound
voice_mod.sfx = sfx_mod
sys.modules["core.voice"] = voice_mod
sys.modules["core.voice.sfx"] = sfx_mod

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
import app.controllers.social_fsm as social_fsm_module


def test_config_values_override_defaults():
    cfg = {
        "behavior": {
            "social_fsm": {
                "deadband_x": 0.5,
                "lock_frames_needed": 10,
                "miss_release": 7,
                "interact_ms": 2000,
                "min_score": 0.75,
                "cooldown_ms": 1200,
                "meow_cooldown_min": 6,
                "meow_cooldown_max": 12,
            }
        }
    }
    fsm = SocialFSM(VisionService(), MovementService(), cfg)
    assert fsm.deadband_x == 0.5
    assert fsm.lock_frames_needed == 10
    assert fsm.miss_release == 7
    assert fsm.interact_ms == 2000
    assert fsm.min_score == 0.75
    assert fsm.cooldown == 1.2
    assert fsm.meow_cooldown_min == 6
    assert fsm.meow_cooldown_max == 12


def test_none_config_values_fallback():
    cfg = {
        "behavior": {
            "social_fsm": {
                "min_score": None,
                "cooldown_ms": None,
                "meow_cooldown_min": None,
                "meow_cooldown_max": None,
            }
        }
    }
    fsm = SocialFSM(VisionService(), MovementService(), cfg)
    assert fsm.min_score == 0.0
    assert fsm.cooldown == 0.0
    assert fsm.meow_cooldown_min == 5.0
    assert fsm.meow_cooldown_max == 15.0
    fsm.on_frame({"score": None, "faces": []}, 0.1)


def test_meow_cooldown_respected(monkeypatch):
    fsm = SocialFSM(VisionService(), MovementService())
    calls = []

    def fake_play_sound(_):
        calls.append(1)

    monkeypatch.setattr(social_fsm_module, "play_sound", fake_play_sound)

    t = 100.0

    def fake_monotonic():
        return t

    monkeypatch.setattr(social_fsm_module.time, "monotonic", fake_monotonic)

    fsm._on_interact()
    assert len(calls) == 1
    next_time = fsm._next_meow_time
    assert 5.0 <= next_time - t <= 15.0

    t += 1.0
    fsm._on_interact()
    assert len(calls) == 1

    t = next_time
    fsm._on_interact()
    assert len(calls) == 2

