"""Utility helpers for simple text based leg calibration files.

This module was extracted from :mod:`Control` to make file I/O
independent from the controller logic.  It uses :class:`pathlib.Path`
so the functions are easy to unit test and mock.
"""
from __future__ import annotations

from pathlib import Path
from typing import List


def read_from_txt(name: str) -> List[List[int]]:
    """Read a matrix of integers from ``name``.

    ``name`` should be provided without extension.  The file is
    expected to contain tab separated values where each line represents
    a row of integers.
    """
    path = Path(__file__).with_name(f"{name}.txt")
    lines = path.read_text().splitlines()
    return [[int(col) for col in line.split("\t")] for line in lines]


def save_to_txt(matrix: List[List[int]], name: str) -> None:
    """Persist ``matrix`` into ``name`` using tab separated values."""
    path = Path(__file__).with_name(f"{name}.txt")
    with path.open("w") as fh:
        for row in matrix:
            fh.write("\t".join(str(v) for v in row) + "\n")
