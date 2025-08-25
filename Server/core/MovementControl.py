from __future__ import annotations

from movement.controller import (
    AttitudeCmd,
    HeightCmd,
    MovementController,
    RelaxCmd,
    GreetCmd,
    StepCmd,
    StopCmd,
    TurnCmd,
    WalkCmd,
)
from movement.hardware import Hardware
from movement.logger import MovementLogger


class MovementControl:
    """High-level façade queuing movement commands."""

    def __init__(
        self,
        hardware: Hardware | None = None,
        logger: MovementLogger | None = None,
        *,
        imu: object | None = None,
        odom: object | None = None,
    ) -> None:
        self.controller = MovementController(
            hardware=hardware,
            logger=logger,
            imu=imu,
            odom=odom,
        )

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

    def greet(self) -> None:
        """\brief Perform a greeting action."""
        self.controller.queue.put(GreetCmd())

    def set_speed(self, speed: int) -> None:
        """\brief Set the controller speed.

        Exposes :meth:`MovementController.set_speed` so that callers (and
        tests) can adjust the execution speed before issuing commands such as
        :class:`StepCmd`.

        Parameters
        ----------
        speed:
            Target speed value to apply.
        """
        self.controller.set_speed(speed)

    def tick(self, dt: float) -> None:
        """Process pending commands.

        Parameters
        ----------
        dt:
            Time step in seconds.
        """
        self.controller.tick(dt)

    def start_loop(self, rate_hz: float = 100.0) -> None:
        """Blocking loop repeatedly calling :meth:`tick`.

        The loop runs at ``rate_hz`` using ``time.monotonic`` for timing and
        delegates to :class:`MovementController`.
        """
        self.controller.start_loop(rate_hz)
