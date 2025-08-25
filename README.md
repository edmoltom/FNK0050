# FNK0050

Utilities and experiments for controlling a small quadruped robot.

## Gesture support

The movement server exposes a :class:`Gestures` helper for scripted leg
motions.  Gestures consist of sequences of absolute foot coordinates and are
advanced in a non-blocking manner by repeatedly calling ``update(dt)`` within
the main control loop.

To add a custom gesture:

```python
from Server.core.movement.gestures import Gestures

g = Gestures(controller)
g.add_gesture(
    "wave",
    [
        [[55, 78, 0], [55, 78, 0], [55, 78, 0], [55, 78, 0]],
        [[55, 78, 0], [55, 78, 0], [55, 78, 0], [80, 23, 0]],
    ],
    [0.5, 0.5],
)
g.start("wave")
```
