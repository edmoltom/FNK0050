"""Simple loader for vision JSON profiles."""
from __future__ import annotations
import json
from typing import Dict

_profiles: Dict[str, dict] = {}


def load_profile(name: str, path: str) -> None:
    """Load a profile JSON from ``path`` and store under ``name``."""
    with open(path, "r", encoding="utf-8") as f:
        _profiles[name] = json.load(f)


def get_config(name: str) -> dict:
    """Return previously loaded profile ``name`` or empty dict."""
    return dict(_profiles.get(name, {}))
