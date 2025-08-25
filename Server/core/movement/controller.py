"""High level movement controller.

The module implements the orchestration layer described in the project
README::

    MovementControl → queue → controller → gait_runner/kinematics/posture → hardware

``MovementControl`` is a light façade used by the network layer.  It
simply enqueues commands which are then consumed by
:class:`MovementController`.  The controller translates these commands
into leg positions through the :mod:`gait_runner`,
:mod:`kinematics` and :mod:`posture` helpers before finally sending the
resulting angles to the :mod:`hardware` abstraction.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any, Optional, Union

from . import gait_runner, kinematics, posture
from .hardware import Hardware
from .logger import MovementLogger


@dataclass
class WalkCmd:
    vx: float
    vy: float
    omega: float


@dataclass
class StepCmd:
    direction: str
    distance: float


@dataclass
class TurnCmd:
    yaw_rate: float


@dataclass
class HeightCmd:
    z: float


@dataclass
class AttitudeCmd:
    roll: float
    pitch: float
    yaw: float


@dataclass
class StopCmd:
    pass


@dataclass
class RelaxCmd:
    pass


Command = Union[WalkCmd, StepCmd, TurnCmd, HeightCmd, AttitudeCmd, StopCmd, RelaxCmd]


class MovementController:
    """Consume commands and drive the robot accordingly."""

    FL, RL, RR, FR = 0, 1, 2, 3
    X, Y, Z = 0, 1, 2
    MAX_SPEED_LIMIT = 200
    MIN_SPEED_LIMIT = 20

    def __init__(self, hardware: Hardware, gait: Any, logger: MovementLogger, config: Optional[dict] = None) -> None:
        self.hardware = hardware
        self.cpg = hardware.cpg
        self.logger = logger
        self.config = config or {}
        self.state = "idle"
        self.queue: Queue[Command] = Queue()
        self.setup_state()
        self.hardware.calibration(self.point, self.angle)

    # ------------------------------------------------------------------
    def setup_state(self) -> None:
        self.speed = self.MIN_SPEED_LIMIT
        self.height = 99
        self.step_height = 10
        self.step_length = 15
        self.order = ["", "", "", "", ""]
        self.point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
        self.angle = [[90, 0, 0], [90, 0, 0], [90, 0, 0], [90, 0, 0]]
        self._prev_yaw = None
        self._prev_t = None
        self._prev_t_gait = None
        self._gait_angle = 0.0
        self._yr = 0.0
        self._is_turning = False
        self._turn_dir = 0
        self._stride_dir_x = 1
        self._stride_dir_z = 0
        self.stop_requested = False

    # ------------------------------------------------------------------
    def set_leg_position(self, leg: int, x: float, y: float, z: float) -> None:
        self.point[leg][self.X] = x
        self.point[leg][self.Y] = y
        self.point[leg][self.Z] = z

    # ------------------------------------------------------------------
    def update_angles_from_points(self) -> None:
        for i in range(4):
            self.angle[i][0], self.angle[i][1], self.angle[i][2] = kinematics.coordinate_to_angle(
                self.point[i][self.X], self.point[i][self.Y], self.point[i][self.Z]
            )

    # ------------------------------------------------------------------
    def run(self) -> None:
        if self.checkPoint():
            try:
                self.update_angles_from_points()
                self.hardware.apply_calibration_to_angles(self.angle)
                self.hardware.send_angles_to_servos(self.angle)
                self.logger.log_current_state(self)
            except Exception as e:
                print("Exception during run():", e)
        else:
            print("This coordinate point is out of the active range")

    # ------------------------------------------------------------------
    def checkPoint(self) -> bool:
        flag = True
        leg_lenght = [0, 0, 0, 0, 0, 0]
        for i in range(4):
            leg_lenght[i] = (self.point[i][0] ** 2 + self.point[i][1] ** 2 + self.point[i][2] ** 2) ** 0.5
        for i in range(4):
            if leg_lenght[i] > 130 or leg_lenght[i] < 25:
                flag = False
        return flag

    # ------------------------------------------------------------------
    def wait_for_next_tick(self, last_tick: float, tick_time: float) -> float:
        next_tick = last_tick + tick_time
        now = time.monotonic()
        time.sleep(max(0, next_tick - now))
        return next_tick

    # ------------------------------------------------------------------
    def clamp_speed(self, min_val: Optional[int] = None, max_val: Optional[int] = None) -> None:
        if min_val is None:
            min_val = self.MIN_SPEED_LIMIT
        if max_val is None:
            max_val = self.MAX_SPEED_LIMIT
        self.speed = max(min_val, min(self.speed, max_val))

    # ------------------------------------------------------------------
    def speed_scale(self) -> float:
        rng = max(1, self.MAX_SPEED_LIMIT - self.MIN_SPEED_LIMIT)
        return max(0.0, min(1.0, (self.speed - self.MIN_SPEED_LIMIT) / rng))

    # ------------------------------------------------------------------
    def changeCoordinates(self, move_order: str, X1: float = 0, Y1: float = 96, Z1: float = 0, X2: float = 0, Y2: float = 96, Z2: float = 0, pos: Optional[Any] = None) -> None:  # noqa: N802,E501
        if pos is None:
            import numpy as np
            pos = np.mat(np.zeros((3, 4)))
        if move_order == "turnLeft":
            self.set_leg_position(self.FL, -X1 + 10, Y1, Z1 + 10)
            self.set_leg_position(self.RL, -X2 + 10, Y2, -Z2 + 10)
            self.set_leg_position(self.RR, X1 + 10, Y1, -Z1 - 10)
            self.set_leg_position(self.FR, X2 + 10, Y2, Z2 - 10)
        elif move_order == "turnRight":
            self.set_leg_position(self.FL, X1 + 10, Y1, -Z1 + 10)
            self.set_leg_position(self.RL, X2 + 10, Y2, Z2 + 10)
            self.set_leg_position(self.RR, -X1 + 10, Y1, -Z1 - 10)
            self.set_leg_position(self.FR, -X2 + 10, Y2, -Z2 - 10)
        elif move_order in ["height", "horizon"]:
            for i in range(2):
                self.set_leg_position(3 * i, X1 + 10, Y1, self.point[3 * i][self.Z])
                self.set_leg_position(1 + i, X2 + 10, Y2, self.point[1 + i][self.Z])
        elif move_order == "Attitude Angle":
            for i in range(2):
                self.set_leg_position(3 - i, pos[0, 1 + 2 * i] + 10, pos[2, 1 + 2 * i], pos[1, 1 + 2 * i])
                self.set_leg_position(i, pos[0, 2 * i] + 10, pos[2, 2 * i], pos[1, 2 * i])
        else:
            for i in range(2):
                self.set_leg_position(i * 2, X1 + 10, Y1, Z1 + ((-1) ** i) * 10)
                self.set_leg_position(i * 2 + 1, X2 + 10, Y2, Z2 + ((-1) ** i) * 10)
        self.run()

    # ------------------------------------------------------------------
    def relax(self, flag: bool = False) -> None:
        self._is_turning = False
        self._turn_dir = 0
        self._stride_dir_x = 0
        self._stride_dir_z = 0
        self.stop_requested = True
        if flag:
            p = [[55, 78, 0], [55, 78, 0], [55, 78, 0], [55, 78, 0]]
            for i in range(4):
                p[i][0] = (self.point[i][0] - p[i][0]) / 50
                p[i][1] = (self.point[i][1] - p[i][1]) / 50
                p[i][2] = (self.point[i][2] - p[i][2]) / 50
            for _ in range(1, 51):
                for i in range(4):
                    self.point[i][0] -= p[i][0]
                    self.point[i][1] -= p[i][1]
                    self.point[i][2] -= p[i][2]
                self.run()
        else:
            gait_runner.stop(self)

    # ------------------------------------------------------------------
    def _process_command(self, cmd: Command) -> None:
        if isinstance(cmd, WalkCmd):
            if cmd.vx > 0:
                gait_runner.forWard(self)
            elif cmd.vx < 0:
                gait_runner.backWard(self)
            elif cmd.vy > 0:
                gait_runner.stepLeft(self)
            elif cmd.vy < 0:
                gait_runner.stepRight(self)
            elif cmd.omega > 0:
                gait_runner.turnLeft(self)
            elif cmd.omega < 0:
                gait_runner.turnRight(self)
        elif isinstance(cmd, StepCmd):
            if cmd.direction == "left":
                gait_runner.stepLeft(self)
            elif cmd.direction == "right":
                gait_runner.stepRight(self)
            elif cmd.direction == "forward":
                gait_runner.forWard(self)
            elif cmd.direction == "backward":
                gait_runner.backWard(self)
        elif isinstance(cmd, TurnCmd):
            if cmd.yaw_rate > 0:
                gait_runner.turnLeft(self)
            elif cmd.yaw_rate < 0:
                gait_runner.turnRight(self)
        elif isinstance(cmd, HeightCmd):
            posture.up_and_down(self, cmd.z)
        elif isinstance(cmd, AttitudeCmd):
            posture.attitude(self, cmd.roll, cmd.pitch, cmd.yaw)
        elif isinstance(cmd, StopCmd):
            gait_runner.stop(self)
        elif isinstance(cmd, RelaxCmd):
            self.relax()

    # ------------------------------------------------------------------
    def tick(self, dt: float) -> None:
        try:
            cmd = self.queue.get_nowait()
        except Empty:
            return
        self._process_command(cmd)

    # ------------------------------------------------------------------
    def start_loop(self, dt: float = 0.01) -> None:
        while True:
            self.tick(dt)
            time.sleep(dt)
