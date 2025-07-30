import Gamepad
import time
import threading

from Action import Action

DEADZONE = 0.2

def polling_loop(gamepad, action):
    
    while(True):
        try:
            x = gamepad.axis(0)
            y = gamepad.axis(1)

            if abs(x) < DEADZONE and abs(y) < DEADZONE:
                action.state = 'idle'
            else:
                action.current_speed = max(1, int(action.max_speed * max(abs(x), abs(y))))
                if x > DEADZONE:
                    action.state = 'turning_right'
                elif x < -DEADZONE:
                    action.state = 'turning_left'
                elif y < -DEADZONE:
                    action.state = 'walking_forward'
                elif y > DEADZONE:
                    action.state = 'walking_backward'

            if gamepad.isPressed('A'):
                action.state = 'greeting'

            time.sleep(0.1)

        except Exception as e:
            print("Polling error:", e)
            break


def main():
    print("Test Gamepad")

    try:
        gamepad = Gamepad.Xbox360()
        gamepad.startBackgroundUpdates()

        action = Action()

        thread = threading.Thread(target=polling_loop, args=(gamepad, action))
        thread.daemon = True  # will be closed with main script
        thread.start()

        print("Connected")
  
    except Exception as e:
        print("Can't link with:", e)
        return

if __name__ == "__main__":
    main()