import Gamepad
import time
import threading

from Action import Action

def polling_loop(gamepad, action):

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
                action.current_speed = max(1, int(action.max_speed * max(abs(x0), abs(y0))))
                if x0 > DEADZONE:
                    action.state = 'turning_right'
                elif x0 < -DEADZONE:
                    action.state = 'turning_left'
                elif y0 < -DEADZONE:
                    action.state = 'walking_forward'
                elif y0 > DEADZONE:
                    action.state = 'walking_backward'

            elif (abs(x1) > DEADZONE or abs(y1) > DEADZONE):
                action.current_speed = max(1, int(action.max_speed * max(abs(x1), abs(y1))))
                if x1 > DEADZONE:
                    action.state = 'step_right'
                elif x1 < -DEADZONE:
                    action.state = 'step_left'

            elif gamepad.isPressed('A') and not prev_A:
                action.state = 'greeting'

            elif gamepad.isPressed('B') and not prev_B:
                action.state = 'relax'

            else:
                action.state = 'idle'

            prev_A = gamepad.isPressed('A')
            prev_B = gamepad.isPressed('B')

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

        action = Action()

        if (test_mode == False):
            thread = threading.Thread(target=polling_loop, args=(gamepad, action))
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
