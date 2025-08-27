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
from pathlib import Path

from . import kinematics, posture, data
from .gait_runner import GaitRunner
from .hardware import Hardware
from .logger import MovementLogger
from .gestures import GesturePlayer, load_sequence_json, Keyframe
from copy import deepcopy


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
class HeadCmd:
    angle_deg: float
    duration_ms: int = 0


@dataclass
class HeadPctCmd:
    pct: float
    duration_ms: int = 0


@dataclass
class StopCmd:
    pass


@dataclass
class RelaxCmd:
    to_pose: bool = True

@dataclass
class GestureCmd:
    """Generic gesture request (non-blocking animation)."""
    name: str  # e.g., "greet"


Command = Union[
    WalkCmd,
    StepCmd,
    TurnCmd,
    HeightCmd,
    AttitudeCmd,
    HeadCmd,
    HeadPctCmd,
    StopCmd,
    RelaxCmd,
    GestureCmd,
]


class MovementController:
    """Consume commands and drive the robot accordingly."""

    FL, RL, RR, FR = 0, 1, 2, 3
    X, Y, Z = 0, 1, 2
    MAX_SPEED_LIMIT = 200
    MIN_SPEED_LIMIT = 20

    def __init__(
        self,
        hardware: Optional[Hardware] = None,
        gait: Optional[Any] = None,
        logger: Optional[MovementLogger] = None,
        *,
        imu: Optional[Any] = None,
        odom: Optional[Any] = None,
        config: Optional[dict] = None,
    ) -> None:
        """Create a new movement controller.

        Parameters
        ----------
        hardware:
            Optional pre-configured :class:`Hardware` bundle.  If omitted a
            new one will be created.
        gait:
            Optional CPG or gait runner to drive the legs.  Defaults to the
            CPG embedded in ``hardware``.
        logger:
            Optional movement logger instance.
        imu, odom:
            Optional IMU and odometry instances forwarded to
            :class:`Hardware` when it needs to construct its own bundle.
        """
        self.hardware = hardware or Hardware(imu=imu, odom=odom)
        self.gait = GaitRunner(gait or self.hardware.cpg)
        self.cpg = self.gait.cpg
        self.logger = logger or MovementLogger()
        self.config = config or {}
        self.head_channel = int(self.config.get("head_channel", 15))
        self.head_min_deg = float(self.config.get("head_min_deg", 20.0))
        self.head_max_deg = float(self.config.get("head_max_deg", 160.0))
        self.head_center_deg = float(self.config.get("head_center_deg", 90.0))
        self.head_inverted = bool(self.config.get("head_inverted", False))
        self._head_angle_deg = self.head_center_deg
        self.state = "idle"
        self.queue: Queue[Command] = Queue()
        self.setup_state()
        self.hardware.calibration(self.point, self.angle)
        # Internal command tracking
        self._active_cmd: Optional[Command] = None
        self._cmd_cycles_remaining: int = 0
        self._prev_phase: float = 0.0
        self._gait_enabled: bool = True
        self.torque_off: bool = False
        self.gestures = GesturePlayer(controller=self, hardware=self.hardware, kinematics=kinematics, tick_hz=100.0)
        # Registered gesture builders. Values are callables returning a Sequence
        # when passed the controller instance. Custom gestures can be provided
        # via JSON files under ``gestures/`` and are loaded on-demand.
        self._gesture_builders = {}

    # ------------------------------------------------------------------
    def setup_state(self) -> None:
        # Start with a speed above the minimum limit so the controller moves
        # at a sensible pace by default. Tests can still adjust this value via
        # :meth:`set_speed` exposed on :class:`MovementControl`.
        self.speed = 120
        self.height = 99
        self.step_height = 10
        self.step_length = 15
        self.order = ["", "", "", "", ""]
        self.point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
        self.angle = [[90, 0, 0], [90, 0, 0], [90, 0, 0], [90, 0, 0]]
        self._prev_t_gait = None
        self._is_turning = False
        self._turn_dir = 0
        self._stride_dir_x = 1
        self._stride_dir_z = 0
        self.stop_requested = False

    # ------------------------------------------------------------------
    def set_speed(self, speed: int) -> None:
        """Update the controller speed.

        Parameters
        ----------
        speed:
            New target speed value. Values outside the permitted range are
            clamped to remain within :data:`MIN_SPEED_LIMIT` and
            :data:`MAX_SPEED_LIMIT`.
        """
        self.speed = speed
        self.clamp_speed()

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
        if self.torque_off:
            self.hardware.relax()
            return
        if self.checkPoint():
            try:
                self.update_angles_from_points()
                self.hardware.apply_angles(self.angle)
                if self.logger.active:
                    self.logger.log_state(time.time(), self.hardware.imu, self.point, self.hardware.odom)
            except Exception as e:
                print("Exception during run():", e)
        else:
            print("This coordinate point is out of the active range")

    # ------------------------------------------------------------------
    def apply_servo_overrides(self, overrides: dict[int, float]) -> None:
        """Direct servo channel overrides with head clamping."""
        pwm = getattr(self.hardware, "servo", None)
        if not pwm:
            return
        func = getattr(pwm, "setServoAngle", None) or getattr(pwm, "set_servo_angle", None)
        if not func:
            return
        for ch, deg in overrides.items():
            if ch == self.head_channel:
                deg = max(self.head_min_deg, min(self.head_max_deg, deg))
                self._head_angle_deg = deg
            func(ch, deg)

    # ------------------------------------------------------------------
    def set_head(self, angle_deg: float, duration_ms: int = 0) -> None:
        """Move the head servo to ``angle_deg`` optionally over ``duration_ms``."""
        target = max(self.head_min_deg, min(self.head_max_deg, angle_deg))
        if self.head_inverted:
            target = self.head_max_deg - (target - self.head_min_deg)
        start = getattr(self, "_head_angle_deg", self.head_center_deg)
        if duration_ms <= 0 or not hasattr(self.hardware, "servo"):
            self.apply_servo_overrides({self.head_channel: target})
            return
        steps = max(1, duration_ms // 20)
        step_ms = duration_ms / steps
        for i in range(1, steps + 1):
            deg = start + (target - start) * (i / steps)
            self.apply_servo_overrides({self.head_channel: deg})
            time.sleep(step_ms / 1000.0)

    # ------------------------------------------------------------------
    def set_head_pct(self, pct: float, duration_ms: int = 0) -> None:
        """Move the head based on a 0-100 percentage of its range."""
        pct = max(0.0, min(100.0, pct))
        if pct <= 50.0:
            angle = self.head_min_deg + (self.head_center_deg - self.head_min_deg) * (pct / 50.0)
        else:
            angle = self.head_center_deg + (self.head_max_deg - self.head_center_deg) * ((pct - 50.0) / 50.0)
        self.set_head(angle, duration_ms)

    # ------------------------------------------------------------------
    def head_center(self) -> None:
        """Convenience to centre the head."""
        self.set_head_pct(50.0, 0)

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
        if getattr(self, "_in_relax", False):
            return
        self._in_relax = True
        self._is_turning = False
        self._turn_dir = 0
        self._stride_dir_x = 0
        self._stride_dir_z = 0
        self._gait_enabled = False
        self.stop_requested = False
        self.torque_off = False
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
        self.cpg.set_velocity(0.0, 0.0, 0.0)

    # ------------------------------------------------------------------
    def load_points_from_file(self, path: Path) -> None:
        """Replace current leg points with coordinates from ``path``."""
        self.point = data.load_points(path)

    # ------------------------------------------------------------------
    def save_points_to_file(self, path: Path) -> None:
        """Persist current leg points into ``path``."""
        data.save_points(path, self.point)

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _play_gesture(self, name: str) -> None:
        """Play a named gesture if available.

        Custom gestures are searched as JSON files under a ``gestures``
        directory located next to this module. When first requested, the
        gesture is lazily registered so subsequent calls reuse the cached
        builder.
        """

        builder = self._gesture_builders.get(name)
        if builder is None:
            module_dir = Path(__file__).resolve().parent
            json_path = module_dir / "gestures" / f"{name}.json"
            if json_path.exists():
                # Register a loader that ignores the controller instance but
                # matches the expected callable signature.
                self._gesture_builders[name] = builder = (
                    lambda _ctrl, p=json_path: load_sequence_json(str(p))
                )

        if builder is None:
            return

        self.stop_requested = False
        self.torque_off = False
        self._gait_enabled = False
        seq = builder(self)
        if seq.frames and seq.frames[0].t_ms > 0:
            seq.frames.insert(0, Keyframe(t_ms=0, legs=deepcopy(self.point)))
        self.gestures.play(seq, blocking=False)

    # ------------------------------------------------------------------
    def _process_command(self, cmd: Command) -> None:
        if isinstance(cmd, (WalkCmd, StepCmd, TurnCmd, HeightCmd, AttitudeCmd, StopCmd, GestureCmd, HeadCmd, HeadPctCmd)):
            self._in_relax = False
        if isinstance(cmd, WalkCmd):
            self.stop_requested = False
            self.torque_off = False
            self._gait_enabled = True
            self._stride_dir_x = 1 if cmd.vx > 0 else -1 if cmd.vx < 0 else 0
            self._stride_dir_z = 1 if cmd.vy > 0 else -1 if cmd.vy < 0 else 0
            self._is_turning = cmd.omega != 0
            self._turn_dir = 1 if cmd.omega > 0 else -1 if cmd.omega < 0 else 0
            self.cpg.set_velocity(cmd.vx, cmd.vy, cmd.omega)
            self._active_cmd = cmd
        elif isinstance(cmd, StepCmd):
            self.stop_requested = False
            self.torque_off = False
            self._gait_enabled = True
            self.clamp_speed()
            scale = self.speed_scale()
            self._is_turning = False
            self._turn_dir = 0
            if cmd.direction == "left":
                self.cpg.set_velocity(0.0, scale, 0.0)
                self._stride_dir_x, self._stride_dir_z = 0, 1
            elif cmd.direction == "right":
                self.cpg.set_velocity(0.0, -scale, 0.0)
                self._stride_dir_x, self._stride_dir_z = 0, -1
            elif cmd.direction == "forward":
                self.cpg.set_velocity(scale, 0.0, 0.0)
                self._stride_dir_x, self._stride_dir_z = 1, 0
            elif cmd.direction == "backward":
                self.cpg.set_velocity(-scale, 0.0, 0.0)
                self._stride_dir_x, self._stride_dir_z = -1, 0
            self._cmd_cycles_remaining = max(1, int(cmd.distance))
            self._prev_phase = self.cpg.phi[0]
            self._active_cmd = cmd
        elif isinstance(cmd, TurnCmd):
            self.stop_requested = False
            self.torque_off = False
            self._gait_enabled = True
            self._stride_dir_x = 0
            self._stride_dir_z = 0
            self._is_turning = cmd.yaw_rate != 0
            self._turn_dir = 1 if cmd.yaw_rate > 0 else -1 if cmd.yaw_rate < 0 else 0
            self.cpg.set_velocity(0.0, 0.0, cmd.yaw_rate)
            self._active_cmd = cmd
        elif isinstance(cmd, HeightCmd):
            self.stop_requested = False
            self.torque_off = False
            self._gait_enabled = False
            posture.up_and_down(self, cmd.z)
            self._active_cmd = None
        elif isinstance(cmd, AttitudeCmd):
            self.stop_requested = False
            self.torque_off = False
            self._gait_enabled = False
            posture.attitude(self, cmd.roll, cmd.pitch, cmd.yaw)
            self._active_cmd = None
        elif isinstance(cmd, StopCmd):
            self.stop_requested = False
            self.torque_off = False
            self._gait_enabled = False
            self.cpg.set_velocity(0.0, 0.0, 0.0)
            self._stride_dir_x = 0
            self._stride_dir_z = 0
            self._is_turning = False
            self._turn_dir = 0
            self._active_cmd = None
        elif isinstance(cmd, GestureCmd):
            self._in_relax = False
            self._play_gesture(cmd.name)
            self._active_cmd = None
        elif isinstance(cmd, HeadCmd):
            self._in_relax = False
            self.stop_requested = False
            self.set_head(cmd.angle_deg, cmd.duration_ms)
            self._active_cmd = None
        elif isinstance(cmd, HeadPctCmd):
            self._in_relax = False
            self.stop_requested = False
            self.set_head_pct(cmd.pct, cmd.duration_ms)
            self._active_cmd = None
        elif isinstance(cmd, RelaxCmd):
            self._gait_enabled = False
            self.relax(flag=cmd.to_pose)
            self.stop_requested = False
            self.torque_off = False
            self._active_cmd = None

    # ------------------------------------------------------------------
    def tick(self, dt: float) -> None:
        # Drain queue and update the active command/state
        try:
            while True:
                cmd = self.queue.get_nowait()
                self._process_command(cmd)
        except Empty:
            pass

        # Track progress for finite commands (e.g. StepCmd)
        if isinstance(self._active_cmd, StepCmd):
            phase = self.cpg.phi[0]
            if phase < self._prev_phase:
                self._cmd_cycles_remaining -= 1
            self._prev_phase = phase
            if self._cmd_cycles_remaining <= 0:
                # Step finished -> stop movement
                self.cpg.set_velocity(0.0, 0.0, 0.0)
                self._stride_dir_x = 0
                self._stride_dir_z = 0
                self._is_turning = False
                self._turn_dir = 0
                self._active_cmd = None
        if self.gestures.is_playing():
            return
        if self._gait_enabled and not self.stop_requested:
            self.gait.update_legs_from_cpg(self, dt)
        self.run()

    # ------------------------------------------------------------------
    def start_loop(self, rate_hz: float = 100.0) -> None:
        tick_time = 1.0 / rate_hz
        last = time.monotonic()
        while True:
            now = time.monotonic()
            dt = now - last
            last = now
            self.tick(dt)
            sleep_time = tick_time - (time.monotonic() - now)
            if sleep_time > 0:
                time.sleep(sleep_time)
