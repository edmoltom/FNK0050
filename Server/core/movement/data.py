"""Utility helpers for simple text based leg calibration files.

This module was extracted from :mod:`Control` to make file I/O
independent from the controller logic.  It uses :class:`pathlib.Path`
so the functions are easy to unit test and mock.
"""
from __future__ import annotations

from pathlib import Path
from typing import List


def load_points(path: Path) -> List[List[int]]:
    """Return a matrix of integers read from ``path``.

    The expected file format is a series of lines with tab separated
    integers representing the *x*, *y* and *z* coordinates for each
    leg.  Empty trailing lines are ignored.
    """
    lines = path.read_text().splitlines()
    return [[int(col) for col in line.split("\t")] for line in lines if line]


def save_points(path: Path, data: List[List[int]]) -> None:
    """Persist ``data`` into ``path`` using tab separated values."""
    with path.open("w") as fh:
        for row in data:
            fh.write("\t".join(str(v) for v in row) + "\n")


# ---------------------------------------------------------------------------
# Backwards compatible wrappers

def read_from_txt(name: str) -> List[List[int]]:
    """Legacy wrapper around :func:`load_points`.

    ``name`` should be provided without extension.  The file is looked up
    relative to this module.
    """
    return load_points(Path(__file__).with_name(f"{name}.txt"))


def save_to_txt(matrix: List[List[int]], name: str) -> None:
    """Legacy wrapper around :func:`save_points`."""
    save_points(Path(__file__).with_name(f"{name}.txt"), matrix)
