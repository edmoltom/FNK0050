from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.extend([str(ROOT / "lib"), str(ROOT / "core")])

import time
import threading

from Gamepad import Xbox360
from MovementControl import MovementControl


def polling_loop(gamepad, controller):
    """Poll gamepad and enqueue movement commands."""
    DEADZONE = 0.2
    prev_B = False
    while True:
        try:
            x0 = gamepad.axis(0)
            y0 = gamepad.axis(1)
            x1 = gamepad.axis(3)
            y1 = gamepad.axis(4)

            if abs(x0) > DEADZONE or abs(y0) > DEADZONE:
                if x0 > DEADZONE:
                    controller.turn(-1.0)
                elif x0 < -DEADZONE:
                    controller.turn(1.0)
                elif y0 < -DEADZONE:
                    controller.walk(1.0, 0.0, 0.0)
                elif y0 > DEADZONE:
                    controller.walk(-1.0, 0.0, 0.0)
            elif abs(x1) > DEADZONE or abs(y1) > DEADZONE:
                if x1 > DEADZONE:
                    controller.step('right', 1.0)
                elif x1 < -DEADZONE:
                    controller.step('left', 1.0)
            elif gamepad.isPressed('A'):
                controller.greet()
                continue  # Skip queuing stop so greeting plays fully
            else:
                b_pressed = gamepad.isPressed('B')
                if b_pressed and not prev_B:
                    controller.relax()
                    prev_B = True
                    continue
                elif not b_pressed:
                    controller.stop()
                    prev_B = False
                # If B is held, do nothing to avoid repeated RelaxCmd

            time.sleep(0.1)
        except Exception as e:
            print("Polling error:", e)
            break


def main():
    print("Test Gamepad")
    test_mode = False

    try:
        gamepad = Xbox360()
        gamepad.startBackgroundUpdates()

        controller = MovementControl()
        threading.Thread(target=controller.start_loop, daemon=True).start()

        if not test_mode:
            thread = threading.Thread(target=polling_loop, args=(gamepad, controller))
            thread.daemon = True
            thread.start()

        print("Connected")

    except Exception as e:
        print("Can't link with:", e)
        return

    while test_mode:
        eventType, name, value = gamepad.getNextEvent()
        print(f"Evento: {eventType:<6}  |  {name:<12}  |  Valor: {value}")


if __name__ == "__main__":
    main()
