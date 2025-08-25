"""Gait generation helpers based on a Central Pattern Generator (CPG)."""
from __future__ import annotations

import time
from typing import Any


def update_legs_from_cpg(ctrl: Any, dt: float) -> None:
    """Update ``ctrl.point`` using the internal CPG state."""
    Z_BASE = [10, 10, -10, -10]

    phases = ctrl.cpg.update(dt)

    stride_len = int(30 * min(1.0, ctrl.cpg.amp_xy_cur))
    lift_height = int(12 * min(1.0, ctrl.cpg.amp_z_cur))

    base_y = ctrl.height
    sx = getattr(ctrl, "_stride_dir_x", 0)
    sz = getattr(ctrl, "_stride_dir_z", 0)

    if getattr(ctrl, "_is_turning", False) and getattr(ctrl, "_turn_dir", 0) != 0:
        tdir = 1 if getattr(ctrl, "_turn_dir", 0) >= 0 else -1
        for i, ph in enumerate(phases):
            s_m, lift_m = ctrl.cpg.foot_position(
                ph,
                ctrl.cpg.duty_cur,
                stride_len=stride_len / 1000.0,
                lift_height=lift_height / 1000.0,
            )
            s_mm, lift_mm = s_m * 1000.0, lift_m * 1000.0
            x_mult = [-1, -1, +1, +1][i] * tdir
            z_mult = [+1, -1, -1, +1][i] * tdir
            X = 10 + x_mult * s_mm
            Y = base_y - 0.45 * lift_mm
            Z = Z_BASE[i] + z_mult * s_mm
            ctrl.set_leg_position(i, X, Y, Z)
        return

    if sx != 0:
        stride_signed = stride_len * sx
        for i, ph in enumerate(phases):
            s_m, lift_m = ctrl.cpg.foot_position(
                ph,
                ctrl.cpg.duty_cur,
                stride_len=stride_signed / 1000.0,
                lift_height=lift_height / 1000.0,
            )
            s_mm, lift_mm = s_m * 1000.0, lift_m * 1000.0
            X = s_mm + 10
            Y = base_y - 0.45 * lift_mm
            Z = Z_BASE[i]
            ctrl.set_leg_position(i, X, Y, Z)
    elif sz != 0:
        stride_signed = stride_len * sz
        for i, ph in enumerate(phases):
            s_m, lift_m = ctrl.cpg.foot_position(
                ph,
                ctrl.cpg.duty_cur,
                stride_len=stride_signed / 1000.0,
                lift_height=lift_height / 1000.0,
            )
            s_mm, lift_mm = s_m * 1000.0, lift_m * 1000.0
            X = 10
            Y = base_y - 0.45 * lift_mm
            Z = Z_BASE[i] + s_mm
            ctrl.set_leg_position(i, X, Y, Z)
    else:
        for i in range(4):
            ctrl.set_leg_position(i, 10, base_y, Z_BASE[i])


def step_move(ctrl: Any, axis: str, mode: str, direction: str, cycles: int = 1) -> None:
    """Run ``cycles`` of the gait generator according to the direction."""
    ctrl.clamp_speed()
    tick_time = 1.0 / ctrl.speed
    tick = time.monotonic()
    scale = ctrl.speed_scale()

    ctrl._is_turning = False
    ctrl._turn_dir = 0

    if axis == "X":
        vx, vy, wz = (1.0 if direction == "positive" else -1.0) * scale, 0.0, 0.0
        ctrl._stride_dir_x, ctrl._stride_dir_z = (1 if direction == "positive" else -1), 0
    elif axis == "Z":
        vx, vy, wz = 0.0, (1.0 if direction == "positive" else -1.0) * scale, 0.0
        ctrl._stride_dir_x, ctrl._stride_dir_z = 0, (1 if direction == "positive" else -1)
    else:
        vx, vy, wz = 0.0, 0.0, (1.0 if direction == "positive" else -1.0) * scale
        ctrl._stride_dir_x = 0
        ctrl._stride_dir_z = 0
        ctrl._is_turning = True
        ctrl._turn_dir = 1 if direction == "positive" else -1

    ctrl.cpg.set_velocity(vx, vy, wz)

    ctrl.stop_requested = False
    ctrl._prev_t_gait = time.monotonic()
    prev_phase = ctrl.cpg.phi[0]
    done = 0

    while not ctrl.stop_requested and done < cycles:
        now = time.monotonic()
        dt = now - ctrl._prev_t_gait
        ctrl._prev_t_gait = now
        update_legs_from_cpg(ctrl, dt)
        ctrl.run()
        phase0 = ctrl.cpg.phi[0]
        if phase0 < prev_phase:
            done += 1
        prev_phase = phase0
        tick = ctrl.wait_for_next_tick(tick, tick_time)


def forWard(ctrl: Any) -> None:  # noqa: N802
    step_move(ctrl, "X", "forWard", "positive")


def backWard(ctrl: Any) -> None:  # noqa: N802
    step_move(ctrl, "X", "backWard", "negative")


def stepLeft(ctrl: Any) -> None:  # noqa: N802
    step_move(ctrl, "Z", "stepLeft", "positive")


def stepRight(ctrl: Any) -> None:  # noqa: N802
    step_move(ctrl, "Z", "stepRight", "negative")


def turnLeft(ctrl: Any) -> None:  # noqa: N802
    step_move(ctrl, "W", "turnLeft", "positive")


def turnRight(ctrl: Any) -> None:  # noqa: N802
    step_move(ctrl, "W", "turnRight", "negative")


def stop(ctrl: Any) -> None:
    ctrl._is_turning = False
    ctrl._turn_dir = 0
    ctrl._stride_dir_x = 0
    ctrl._stride_dir_z = 0
    ctrl.stop_requested = True

    p = [[10, ctrl.height, 10], [10, ctrl.height, 10], [10, ctrl.height, -10], [10, ctrl.height, -10]]
    for i in range(4):
        p[i][0] = (p[i][0] - ctrl.point[i][0]) / 50
        p[i][1] = (p[i][1] - ctrl.point[i][1]) / 50
        p[i][2] = (p[i][2] - ctrl.point[i][2]) / 50
    for _ in range(50):
        for i in range(4):
            ctrl.point[i][0] += p[i][0]
            ctrl.point[i][1] += p[i][1]
            ctrl.point[i][2] += p[i][2]
        ctrl.run()
