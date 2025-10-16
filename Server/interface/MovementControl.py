"""Interface-level module bridging mind and core layers."""

from __future__ import annotations

import threading

from core.movement.controller import (
    AttitudeCmd,
    HeadCmd,
    HeadPctCmd,
    HeightCmd,
    MovementController,
    RelaxCmd,
    GestureCmd,
    StepCmd,
    StopCmd,
    TurnCmd,
    WalkCmd,
)
from core.movement.hardware import Hardware


class MovementControl:
    """High-level façade queuing movement commands."""

    def __init__(
        self,
        hardware: Hardware | None = None,
        *,
        config: dict | None = None,
    ) -> None:
        self.controller = MovementController(
            hardware=hardware,
            config=config,
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

    def _turn_in_place(self, direction: str, duration_ms: int, speed: float) -> None:
        yaw_rate = speed if direction == "left" else -speed
        self.controller.queue.put(TurnCmd(yaw_rate))
        threading.Timer(duration_ms / 1000.0,
                        lambda: self.controller.queue.put(StopCmd())).start()

    def turn_left(self, duration_ms: int, speed: float) -> None:
        self._turn_in_place("left", duration_ms, speed)

    def turn_right(self, duration_ms: int, speed: float) -> None:
        self._turn_in_place("right", duration_ms, speed)

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

    def head(self, pct: float, duration_ms: int = 0) -> None:
        """\brief Move the head to a yaw percentage.
        \param pct Head yaw as a percentage [0-100].
        \param duration_ms Motion duration in milliseconds.

        The motion is dispatched through :class:`HeadPctCmd`.
        """
        self.controller.queue.put(HeadPctCmd(pct, duration_ms))

    def head_deg(self, angle_deg: float, duration_ms: int = 0) -> None:
        """\brief Move the head to an absolute yaw angle in degrees.
        \param angle_deg Head yaw angle in degrees.
        \param duration_ms Motion duration in milliseconds.

        The motion is dispatched through :class:`HeadCmd`.
        """
        self.controller.queue.put(HeadCmd(angle_deg, duration_ms))

    def head_center(self) -> None:
        """\brief Center the head using :class:`HeadPctCmd`."""
        self.controller.queue.put(HeadPctCmd(50.0, 0))

    def stop(self) -> None:
        """\brief Stop any ongoing motion."""
        self.controller.queue.put(StopCmd())

    def relax(self) -> None:
        """\brief Move to the predefined relaxed pose before releasing torque."""
        self.controller.queue.put(RelaxCmd(to_pose=True))

    def gesture(self, name: str) -> None:
        """\brief Play any named gesture via the controller's gesture engine."""
        self.controller.queue.put(GestureCmd(name=name))

    @property
    def head_limits(self) -> tuple[float, float, float]:
        """Expose head min, max, and center angles from the internal controller."""
        c = self.controller
        return c.head_min_deg, c.head_max_deg, c.head_center_deg

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
