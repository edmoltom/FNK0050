"""Controller package for application components."""

from typing import TYPE_CHECKING

from interface.tracker.visual_tracker import (
    AxisXTurnController,
    AxisYHeadController,
    VisualTracker,
)

__all__ = [
    "FaceTracker",
    "SocialFSM",
    "AxisXTurnController",
    "AxisYHeadController",
    "VisualTracker",
]

if TYPE_CHECKING:  # pragma: no cover
    from mind.behavior.social_fsm import SocialFSM as _SocialFSM
    from mind.perception.face_tracker import FaceTracker as _FaceTracker


def __getattr__(name: str):
    if name == "FaceTracker":
        from mind.perception.face_tracker import FaceTracker

        return FaceTracker
    if name == "SocialFSM":
        from mind.behavior.social_fsm import SocialFSM

        return SocialFSM
    if name == "ObjectTracker":
        from interface.tracker.visual_tracker import VisualTracker

        return VisualTracker
    raise AttributeError(f"module 'app.controllers' has no attribute {name!r}")

