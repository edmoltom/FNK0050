from __future__ import annotations

import time
from dataclasses import dataclass
from queue import Queue, Empty
from typing import Union

from Control import Control


@dataclass
class WalkCmd:
    """\brief Command for continuous walking."""
    vx: float
    vy: float
    omega: float


@dataclass
class StepCmd:
    """\brief Command for a discrete step."""
    direction: str
    distance: float


@dataclass
class TurnCmd:
    """\brief Command for turning."""
    yaw_rate: float


@dataclass
class HeightCmd:
    """\brief Command to change body height."""
    z: float


@dataclass
class AttitudeCmd:
    """\brief Command to set body attitude."""
    roll: float
    pitch: float
    yaw: float


@dataclass
class StopCmd:
    """\brief Command to stop motion."""
    pass


@dataclass
class RelaxCmd:
    """\brief Command to relax servos."""
    pass


Command = Union[WalkCmd, StepCmd, TurnCmd, HeightCmd, AttitudeCmd, StopCmd, RelaxCmd]


class MovementControl:
    """\brief High-level movement façade using queued commands."""

    def __init__(self) -> None:
        """\brief Initialize control interface and command queue."""
        self.control = Control()
        self._queue: Queue[Command] = Queue()

    def walk(self, vx: float, vy: float, omega: float) -> None:
        """\brief Request continuous walking velocity.
        \param vx Forward/backward velocity.
        \param vy Lateral velocity.
        \param omega Yaw rate.
        """
        self._queue.put(WalkCmd(vx, vy, omega))

    def step(self, direction: str, distance: float) -> None:
        """\brief Request a discrete step.
        \param direction Step direction: 'forward', 'backward', 'left' or 'right'.
        \param distance Step length (unused units).
        """
        self._queue.put(StepCmd(direction, distance))

    def turn(self, yaw_rate: float) -> None:
        """\brief Request a turning action.
        \param yaw_rate Desired yaw rate.
        """
        self._queue.put(TurnCmd(yaw_rate))

    def set_height(self, z: float) -> None:
        """\brief Set body height.
        \param z Target height value.
        """
        self._queue.put(HeightCmd(z))

    def set_attitude(self, roll: float, pitch: float, yaw: float) -> None:
        """\brief Set body attitude.
        \param roll Roll angle in degrees.
        \param pitch Pitch angle in degrees.
        \param yaw Yaw angle in degrees.
        """
        self._queue.put(AttitudeCmd(roll, pitch, yaw))

    def stop(self) -> None:
        """\brief Stop any ongoing motion."""
        self._queue.put(StopCmd())

    def relax(self) -> None:
        """\brief Relax the robot servos."""
        self._queue.put(RelaxCmd())

    def tick(self, dt: float) -> None:
        """\brief Process pending commands.
        \param dt Time step in seconds (unused).
        """
        try:
            cmd = self._queue.get_nowait()
        except Empty:
            return

        if isinstance(cmd, WalkCmd):
            if cmd.vx > 0:
                self.control.forWard()
            elif cmd.vx < 0:
                self.control.backWard()
            elif cmd.vy > 0:
                self.control.stepLeft()
            elif cmd.vy < 0:
                self.control.stepRight()
            elif cmd.omega > 0:
                self.control.turnLeft()
            elif cmd.omega < 0:
                self.control.turnRight()
        elif isinstance(cmd, StepCmd):
            if cmd.direction == 'left':
                self.control.stepLeft()
            elif cmd.direction == 'right':
                self.control.stepRight()
            elif cmd.direction == 'forward':
                self.control.forWard()
            elif cmd.direction == 'backward':
                self.control.backWard()
        elif isinstance(cmd, TurnCmd):
            if cmd.yaw_rate > 0:
                self.control.turnLeft()
            elif cmd.yaw_rate < 0:
                self.control.turnRight()
        elif isinstance(cmd, HeightCmd):
            self.control.upAndDown(cmd.z)
        elif isinstance(cmd, AttitudeCmd):
            self.control.attitude(cmd.roll, cmd.pitch, cmd.yaw)
        elif isinstance(cmd, StopCmd):
            self.control.stop()
        elif isinstance(cmd, RelaxCmd):
            self.control.relax()

    def start_loop(self, dt: float = 0.01) -> None:
        """\brief Blocking loop repeatedly calling tick.
        \param dt Loop period in seconds.
        """
        while True:
            self.tick(dt)
            time.sleep(dt)
