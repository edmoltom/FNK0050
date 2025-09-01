from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
from types import SimpleNamespace
from pathlib import Path
import json
import time
import threading
from copy import deepcopy

@dataclass
class Keyframe:
    """A single absolute pose for all legs at a given time.

    @param t_ms Absolute time within the sequence in milliseconds.
    @param legs List of 4 triples [x, y, z] in millimetres (absolute foot positions).
    @param servo_overrides Optional raw servo channel → angle degrees for one-off effects.
    """
    t_ms: int
    legs: List[List[float]]
    servo_overrides: Optional[Dict[int, float]] = None

    def __post_init__(self) -> None:
        if len(self.legs) != 4:
            raise ValueError("Keyframe must describe 4 legs.")
        for leg in self.legs:
            if len(leg) != 3:
                raise ValueError("Each leg requires 3 coordinates.")

@dataclass
class Sequence:
    """A named list of keyframes describing a gesture.

    @param name Sequence identifier.
    @param frames Ordered list of keyframes.
    @param loop Whether playback restarts after the last frame.
    """
    name: str
    frames: List[Keyframe]
    loop: bool = False

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("Sequence requires at least one keyframe.")

class GesturePlayer:
    """Plays non-locomotion gestures defined as absolute foot trajectories.

    The player linearly interpolates foot XYZ between keyframes and sends
    the resulting joint angles to the hardware each tick.

    Integration:
      - Preferred: use MovementController.set_leg_position(i, x, y, z)
        and rely on the controller's usual apply/flush.
      - Fallback: compute angles via kinematics.coordinate_to_angle and
        call hardware.apply_angles(angle_4x3).

    Thread-safety:
      - play() can run blocking or in a thread; stop() cancels.
    """
    def __init__(self, controller=None, hardware=None, kinematics=None, tick_hz: float = 100.0):
        self.controller = controller
        self.hardware = hardware
        self.kinematics = kinematics
        self.tick_hz = tick_hz
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    # -------- public API --------
    def play(self, seq: Sequence, blocking: bool = False) -> None:
        """Start playing a sequence.

        @param seq Sequence to play.
        @param blocking Run in current thread if True.
        """
        self.stop()
        self._stop.clear()
        if blocking:
            self._run(seq)
        else:
            self._thread = threading.Thread(target=self._run, args=(seq,), daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Request to stop current playback."""
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None

    def is_playing(self) -> bool:
        """Return True if a sequence is currently playing."""
        return self._thread is not None and self._thread.is_alive()

    # -------- helpers --------
    def _run(self, seq: Sequence) -> None:
        if not seq.frames:
            return
        frames = sorted(seq.frames, key=lambda f: f.t_ms)
        period_ms = frames[-1].t_ms
        tick_dt = 1.0 / self.tick_hz

        start = time.monotonic()
        last_apply = start

        while not self._stop.is_set():
            now = time.monotonic()
            elapsed_ms = int((now - start) * 1000)

            if elapsed_ms > period_ms:
                if seq.loop:
                    start = now
                    continue
                break

            f0, f1 = frames[0], frames[-1]
            for i in range(len(frames) - 1):
                if frames[i].t_ms <= elapsed_ms <= frames[i + 1].t_ms:
                    f0, f1 = frames[i], frames[i + 1]
                    break

            span = max(1, f1.t_ms - f0.t_ms)
            alpha = (elapsed_ms - f0.t_ms) / span

            legs = []
            for li in range(4):
                x0, y0, z0 = f0.legs[li]
                x1, y1, z1 = f1.legs[li]
                x = x0 + (x1 - x0) * alpha
                y = y0 + (y1 - y0) * alpha
                z = z0 + (z1 - z0) * alpha
                legs.append([x, y, z])

            self._apply_pose(legs)

            if f1.servo_overrides:
                self._apply_servo_overrides(f1.servo_overrides)

            sleep_left = tick_dt - (time.monotonic() - last_apply)
            if sleep_left > 0:
                time.sleep(sleep_left)
            last_apply = time.monotonic()

    def _apply_pose(self, legs_xyz: List[List[float]]) -> None:
        """Send desired pose to controller/hardware."""
        if self.controller and hasattr(self.controller, "set_leg_position"):
            for i in range(4):
                x, y, z = legs_xyz[i]
                self.controller.set_leg_position(i, x, y, z)
            if hasattr(self.controller, "apply_now"):
                self.controller.apply_now()
            elif hasattr(self.controller, "run"):
                self.controller.run()
            return

        assert self.kinematics is not None and self.hardware is not None, \
            "Kinematics and hardware required for direct apply."
        angle = [[0.0, 0.0, 0.0] for _ in range(4)]
        for i in range(4):
            x, y, z = legs_xyz[i]
            a0, a1, a2 = self.kinematics.coordinate_to_angle(x, y, z)
            angle[i][0] = a0
            angle[i][1] = a1
            angle[i][2] = a2
        self.hardware.apply_angles(angle)

    def _apply_servo_overrides(self, overrides: Dict[int, float]) -> None:
        """Direct servo channel overrides for effects like 'paw wave'."""
        if self.controller and hasattr(self.controller, "apply_servo_overrides"):
            self.controller.apply_servo_overrides(overrides)

# -------- convenience builders --------

def seq_from_table(name: str, table: List[Dict]) -> Sequence:
    """Build a sequence from a list of dict rows.

    Each row:
      {
        "t": <ms>,
        "legs": [[x, y, z], [x, y, z], [x, y, z], [x, y, z]],
        "overrides": {11: 92}   # optional servo overrides
      }

    @param name Sequence name.
    @param table Table of keyframe dictionaries.
    @return Sequence instance.
    """
    frames: List[Keyframe] = []
    for row in table:
        frames.append(Keyframe(
            t_ms=int(row["t"]),
            legs=row["legs"],
            servo_overrides=row.get("overrides")
        ))
    return Sequence(name=name, frames=frames, loop=False)


def load_sequence_json(path: str) -> Sequence:
    """Load a :class:`Sequence` definition from a JSON file.

    The JSON schema mirrors the table accepted by :func:`seq_from_table`::

        {
          "name": "wave",          # optional, defaults to filename stem
          "loop": false,            # optional
          "frames": [
            {"t": 0,
             "legs": [[x, y, z], [x, y, z], [x, y, z], [x, y, z]],
             "overrides": {"11": 92}  # optional servo overrides
            },
            ...
          ]
        }

    Parameters
    ----------
    path:
        Path to the JSON file on disk.

    Returns
    -------
    Sequence
        Parsed sequence instance.
    """

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    name = data.get("name") or Path(path).stem
    table = data.get("frames", [])

    # Ensure override keys are integers for downstream consumers.
    for row in table:
        if "overrides" in row and row["overrides"] is not None:
            row["overrides"] = {int(k): v for k, v in row["overrides"].items()}

    seq = seq_from_table(name, table)
    seq.loop = bool(data.get("loop", False))
    return seq
