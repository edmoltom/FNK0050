"""Kinematic helper functions for the quadruped legs.

The functions here are pure and stateless.  They convert between
Cartesian coordinates and the servo angles of a single leg.  Having
these utilities in a dedicated module keeps the main controller free
from the mathematical details and makes them easier to unit test.
"""
from __future__ import annotations

import math
from typing import Tuple


def coordinate_to_angle(
    x: float,
    y: float,
    z: float,
    l1: float = 23,
    l2: float = 55,
    l3: float = 55,
) -> Tuple[float, float, float]:
    """Convert a target point in millimetres to joint angles.

    The returned tuple contains the three joint angles in degrees for
    the shoulder, thigh and knee respectively.
    """
    a = math.pi / 2 - math.atan2(z, y)
    x_3 = 0
    x_4 = l1 * math.sin(a)
    x_5 = l1 * math.cos(a)
    l23 = math.sqrt((z - x_5) ** 2 + (y - x_4) ** 2 + (x - x_3) ** 2)
    w = (x - x_3) / l23
    v = (l2 * l2 + l23 * l23 - l3 * l3) / (2 * l2 * l23)
    b = math.asin(round(w, 2)) - math.acos(round(v, 2))
    c = math.pi - math.acos(round((l2 ** 2 + l3 ** 2 - l23 ** 2) / (2 * l3 * l2), 2))
    a = round(math.degrees(a))
    b = round(math.degrees(b))
    c = round(math.degrees(c))
    return a, b, c


def angle_to_coordinate(
    a: float,
    b: float,
    c: float,
    l1: float = 23,
    l2: float = 55,
    l3: float = 55,
) -> Tuple[float, float, float]:
    """Inverse of :func:`coordinate_to_angle`.

    Given the joint angles in degrees it returns the corresponding
    ``(x, y, z)`` point in millimetres.
    """
    a = math.pi / 180 * a
    b = math.pi / 180 * b
    c = math.pi / 180 * c
    x = l3 * math.sin(b + c) + l2 * math.sin(b)
    y = l3 * math.sin(a) * math.cos(b + c) + l2 * math.sin(a) * math.cos(b) + l1 * math.sin(a)
    z = l3 * math.cos(a) * math.cos(b + c) + l2 * math.cos(a) * math.cos(b) + l1 * math.cos(a)
    return x, y, z


def clamp(value: float, v_min: float, v_max: float) -> float:
    """Clamp ``value`` to the inclusive range ``[v_min, v_max]``."""
    if value < v_min:
        return v_min
    if value > v_max:
        return v_max
    return value
