import Gamepad
import time
import threading

from movement.controller import Controller


def polling_loop(gamepad, controller, state):
    """Continuously poll the gamepad and drive the controller.

    Any exception (such as a disconnect) resets the previous button states so
    that subsequent connection attempts start cleanly.
    """

    DEADZONE = 0.2

    while True:
        try:
            if not Gamepad.is_connected(gamepad):
                raise IOError("Gamepad disconnected")

            x0 = gamepad.axis(0)
            y0 = gamepad.axis(1)
            x1 = gamepad.axis(3)
            y1 = gamepad.axis(4)

            if (abs(x0) > DEADZONE or abs(y0) > DEADZONE):
                controller.speed = max(
                    1, int(controller.MAX_SPEED_LIMIT * max(abs(x0), abs(y0)))
                )
                if x0 > DEADZONE:
                    controller.turnRight()
                elif x0 < -DEADZONE:
                    controller.turnLeft()
                elif y0 < -DEADZONE:
                    controller.forWard()
                elif y0 > DEADZONE:
                    controller.backWard()

            elif (abs(x1) > DEADZONE or abs(y1) > DEADZONE):
                controller.speed = max(
                    1, int(controller.MAX_SPEED_LIMIT * max(abs(x1), abs(y1)))
                )
                if x1 > DEADZONE:
                    controller.stepRight()
                elif x1 < -DEADZONE:
                    controller.stepLeft()

            elif gamepad.isPressed('A') and not state['prev_A']:
                controller.greet()

            elif gamepad.isPressed('B') and not state['prev_B']:
                controller.relax(True)

            elif not controller.gestures.active:
                controller.stop()

            state['prev_A'] = gamepad.isPressed('A')
            state['prev_B'] = gamepad.isPressed('B')

            # Gestures run asynchronously; ``update`` advances them each tick.
            controller.update(0.1)
            time.sleep(0.1)

        except Exception as e:
            print("Polling error:", e)
            state['prev_A'] = False
            state['prev_B'] = False
            break


def main():

    print("Test Gamepad")
    test_mode = False
    state = {'prev_A': False, 'prev_B': False}

    while True:
        gamepad = None
        try:
            gamepad = Gamepad.Xbox360()
            gamepad.startBackgroundUpdates()

            controller = Controller()

            if not test_mode:
                thread = threading.Thread(target=polling_loop, args=(gamepad, controller, state))
                thread.daemon = True  # will be closed with main script
                thread.start()
                while thread.is_alive() and Gamepad.is_connected(gamepad):
                    time.sleep(0.5)
            else:
                while Gamepad.is_connected(gamepad):
                    eventType, name, value = gamepad.getNextEvent()
                    print(f"Evento: {eventType:<6}  |  {name:<12}  |  Valor: {value}")

            print("Disconnected")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Can't link with:", e)
        finally:
            state['prev_A'] = False
            state['prev_B'] = False
            if gamepad is not None:
                try:
                    gamepad.stopBackgroundUpdates()
                except Exception:
                    pass
            if test_mode:
                break
            print("Reconnecting in 1 second...")
            time.sleep(1)


if __name__ == "__main__":
    main()

