"""Posture related helpers separated from the monolithic controller."""
from __future__ import annotations

import math
from typing import Any

import numpy as np


def map_range(value: float, from_low: float, from_high: float, to_low: float, to_high: float) -> float:
    """Linear mapping of ``value`` from one range to another."""
    return (to_high - to_low) * (value - from_low) / (from_high - from_low) + to_low


def posture_balance(r: float, p: float, y: float, h: float = 1, *, height: float = 99) -> np.matrix:
    """Compute leg positions that keep the body balanced.

    Parameters mirror the original implementation.  ``height`` is the
    nominal body height used when ``h`` is zero.
    """
    b = 76
    w = 76
    l = 136
    if h != 0:
        height = h
    pos = np.mat([0.0, 0.0, h]).T
    rpy = np.array([r, p, y]) * math.pi / 180
    R, P, Y = rpy[0], rpy[1], rpy[2]
    rotx = np.mat([[1, 0, 0], [0, math.cos(R), -math.sin(R)], [0, math.sin(R), math.cos(R)]])
    roty = np.mat([[math.cos(P), 0, -math.sin(P)], [0, 1, 0], [math.sin(P), 0, math.cos(P)]])
    rotz = np.mat([[math.cos(Y), -math.sin(Y), 0], [math.sin(Y), math.cos(Y), 0], [0, 0, 1]])
    rot_mat = rotx * roty * rotz
    body_struc = np.mat([[l / 2, b / 2, 0], [l / 2, -b / 2, 0], [-l / 2, b / 2, 0], [-l / 2, -b / 2, 0]]).T
    footpoint_struc = np.mat([
        [(l / 2), (w / 2) + 10, height - h],
        [(l / 2), (-w / 2) - 10, height - h],
        [(-l / 2), (w / 2) + 10, height - h],
        [(-l / 2), (-w / 2) - 10, height - h],
    ]).T
    AB = np.mat(np.zeros((3, 4)))
    for i in range(4):
        AB[:, i] = pos + rot_mat * footpoint_struc[:, i] - body_struc[:, i]
    return AB


def up_and_down(controller: Any, value: float) -> None:
    """Change the body height."""
    controller.height = value + 99
    controller.changeCoordinates("height", 0, controller.height, 0, 0, controller.height, 0)


def before_and_after(controller: Any, value: float) -> None:
    """Move the body forward/backwards."""
    controller.changeCoordinates("horizon", value, controller.height, 0, value, controller.height, 0)


def attitude(controller: Any, roll: float, pitch: float, yaw: float) -> None:
    """Update the body attitude using roll, pitch and yaw angles."""
    r = map_range(int(roll), -20, 20, -10, 10)
    p = map_range(int(pitch), -20, 20, -10, 10)
    y = map_range(int(yaw), -20, 20, -10, 10)
    pos = posture_balance(r, p, y, 0, height=controller.height)
    controller.changeCoordinates("Attitude Angle", pos=pos)
