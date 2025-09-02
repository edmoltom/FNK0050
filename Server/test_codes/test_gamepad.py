from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.extend([str(ROOT / "lib"), str(ROOT / "core")])

import time
import threading

from peripherals.Gamepad import Xbox360
from MovementControl import MovementControl


DEADZONE = 0.2
last_pct = 50.0


def map_head_pct(y1: float) -> float:
    """Map joystick input to head percentage with smoothing."""
    global last_pct
    if abs(y1) <= DEADZONE:
        target = 50.0
    else:
        norm = (abs(y1) - DEADZONE) / (1 - DEADZONE)
        curve = norm ** 3
        direction = -1.0 if y1 > 0 else 1.0
        target = 50.0 + direction * curve * 50.0
    smoothed = last_pct + (target - last_pct) * 0.2
    last_pct = smoothed
    return smoothed


def polling_loop(gamepad, controller):
    """Poll gamepad and enqueue movement commands."""
    prev_A = False
    prev_B = False
    prev_X = False
    prev_Y = False
    while True:
        try:
            x0 = gamepad.axis(0)
            y0 = gamepad.axis(1)
            x1 = gamepad.axis(3)
            y1 = gamepad.axis(4)
            if abs(y1) > DEADZONE or last_pct != 50.0:
                pct = map_head_pct(y1)
                controller.head(pct)

            if abs(x0) > DEADZONE or abs(y0) > DEADZONE:
                if x0 > DEADZONE:
                    controller.turn(-1.0)
                elif x0 < -DEADZONE:
                    controller.turn(1.0)
                elif y0 < -DEADZONE:
                    controller.walk(1.0, 0.0, 0.0)
                elif y0 > DEADZONE:
                    controller.walk(-1.0, 0.0, 0.0)
            elif abs(x1) > DEADZONE:
                if x1 > DEADZONE:
                    controller.step('right', 1.0)
                elif x1 < -DEADZONE:
                    controller.step('left', 1.0)
            # Edge-trigger A like B (avoid enqueuing every frame)
            elif (gamepad.isPressed('A') and not prev_A):
                controller.gesture("greet")  
                prev_A = True
                continue
            elif (gamepad.isPressed('X') and not prev_X):
                controller.gesture("sit") 
                prev_X = True
                continue
            elif (gamepad.isPressed('Y') and not prev_Y):
                controller.gesture("stand_neutral")  
                prev_Y = True
                continue
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

            prev_A = gamepad.isPressed('A')
            prev_B = gamepad.isPressed('B')
            prev_X = gamepad.isPressed('X')
            prev_Y = gamepad.isPressed('Y')

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
