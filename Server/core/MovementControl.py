from __future__ import annotations

import time

from movement.controller import (
    AttitudeCmd,
    Command,
    HeightCmd,
    MovementController,
    RelaxCmd,
    StepCmd,
    StopCmd,
    TurnCmd,
    WalkCmd,
)
from movement.hardware import Hardware
from movement.logger import MovementLogger


class MovementControl:
    """High-level façade queuing movement commands."""

    def __init__(self, hardware: Hardware | None = None, logger: MovementLogger | None = None) -> None:
        hardware = hardware or Hardware()
        logger = logger or MovementLogger()
        self.controller = MovementController(hardware, hardware.cpg, logger)

    def walk(self, vx: float, vy: float, omega: float) -> None:
        """\brief Request continuous walking velocity.
        \param vx Forward/backward velocity.
        \param vy Lateral velocity.
        \param omega Yaw rate.
        """
        self.controller.queue.put(WalkCmd(vx, vy, omega))

    def step(self, direction: str, distance: float) -> None:
        """\brief Request a discrete step.
        \param direction Step direction: 'forward', 'backward', 'left' or 'right'.
        \param distance Step length (unused units).
        """
        self.controller.queue.put(StepCmd(direction, distance))

    def turn(self, yaw_rate: float) -> None:
        """\brief Request a turning action.
        \param yaw_rate Desired yaw rate.
        """
        self.controller.queue.put(TurnCmd(yaw_rate))

    def set_height(self, z: float) -> None:
        """\brief Set body height.
        \param z Target height value.
        """
        self.controller.queue.put(HeightCmd(z))

    def set_attitude(self, roll: float, pitch: float, yaw: float) -> None:
        """\brief Set body attitude.
        \param roll Roll angle in degrees.
        \param pitch Pitch angle in degrees.
        \param yaw Yaw angle in degrees.
        """
        self.controller.queue.put(AttitudeCmd(roll, pitch, yaw))

    def stop(self) -> None:
        """\brief Stop any ongoing motion."""
        self.controller.queue.put(StopCmd())

    def relax(self) -> None:
        """\brief Relax the robot servos."""
        self.controller.queue.put(RelaxCmd())

    def tick(self, dt: float) -> None:
        """\brief Process pending commands.
        \param dt Time step in seconds (unused).
        """
        self.controller.tick(dt)

    def start_loop(self, dt: float = 0.01) -> None:
        """\brief Blocking loop repeatedly calling tick.
        \param dt Loop period in seconds.
        """
        while True:
            self.tick(dt)
            time.sleep(dt)
