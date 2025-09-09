from unittest.mock import MagicMock
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
# Make Server package available
sys.path.append(str(ROOT / "Server"))

# Provide a stub MovementControl to avoid heavy imports
core_mod = types.ModuleType("core")

class MovementControl:
    def turn_left(self, duration_ms, speed):
        pass

    def turn_right(self, duration_ms, speed):
        pass

core_mod.MovementControl = MovementControl
sys.modules["core"] = core_mod
sys.modules["core.MovementControl"] = core_mod

from app.services.movement_service import MovementService


def test_turn_left_delegates():
    mc = MagicMock(spec=MovementControl)
    svc = MovementService(mc)
    svc.turn_left(100, 1.0)
    mc.turn_left.assert_called_once_with(100, 1.0)


def test_turn_right_delegates():
    mc = MagicMock(spec=MovementControl)
    svc = MovementService(mc)
    svc.turn_right(200, 2.0)
    mc.turn_right.assert_called_once_with(200, 2.0)
