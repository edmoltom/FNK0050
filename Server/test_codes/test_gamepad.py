import Gamepad
import time
import threading

from movement.controller import Controller


def polling_loop(gamepad, controller):

    DEADZONE = 0.2
    prev_A = False
    prev_B = False

    while(True):
        try:
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

            elif gamepad.isPressed('A') and not prev_A:
                controller.gestures.start("greet")

            elif gamepad.isPressed('B') and not prev_B:
                controller.relax(True)

            else:
                controller.stop()

            prev_A = gamepad.isPressed('A')
            prev_B = gamepad.isPressed('B')

            # Gestures run asynchronously; ``update`` advances them each tick.
            controller.update(0.1)
            time.sleep(0.1)

        except Exception as e:
            print("Polling error:", e)
            break


def main():
    
    print("Test Gamepad")
    test_mode = False

    try:
        gamepad = Gamepad.Xbox360()
        gamepad.startBackgroundUpdates()

        controller = Controller()

        if not test_mode:
            thread = threading.Thread(target=polling_loop, args=(gamepad, controller))
            thread.daemon = True  # will be closed with main script
            thread.start()

        print("Connected")
  
    except Exception as e:
        print("Can't link with:", e)
        return
    
    while (test_mode):
        eventType, name, value = gamepad.getNextEvent()
        print(f"Evento: {eventType:<6}  |  {name:<12}  |  Valor: {value}")

if __name__ == "__main__":
    main()

