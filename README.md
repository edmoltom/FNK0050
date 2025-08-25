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

## Gamepad testing

The script `Server/test_codes/test_gamepad.py` demonstrates polling an
Xbox360-style controller. If the gamepad disconnects or another error occurs,
the polling loop clears internal button-state flags (`prev_A` and `prev_B`) and
the main loop waits briefly before attempting to reconnect. The connection
status of a controller can be queried with `Gamepad.is_connected()` to aid
testing when no physical gamepad is present.
