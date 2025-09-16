"""Utility functions for playing short sound effects."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable


def _available_player(players: Iterable[str] = ("aplay", "paplay", "play")) -> str | None:
    """Return the first available player from *players* or ``None``."""
    for player in players:
        if shutil.which(player):
            return player
    return None


def play_sound(path: str | Path) -> None:
    """Play a WAV file at *path* using the first available player.

    If no player is available, the path is printed so the user can play the
    sound manually.
    """
    wav_path = Path(path)
    player = _available_player()
    if player:
        subprocess.run([player, str(wav_path)])
    else:
        print(f"[INFO] WAV ready at {wav_path}")
