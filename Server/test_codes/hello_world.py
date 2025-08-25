"""Simple greeting test using the high level controller.

This script demonstrates the new non-blocking gesture system. Gestures are
started instantly and then progressed by repeatedly calling ``update`` with a
time delta. They can be cancelled at any time via :meth:`relax`.
"""

import time

from movement.controller import Controller

def main():
    print("Hello!! (●'◡'●)")

    controller = Controller()

    # Gestures are tick-driven and do not block. Start the built-in greeting
    # gesture and then advance it in a loop, simulating a main control loop.
    controller.gestures.start("greet")

    for _ in range(20):
        controller.update(0.1)
        time.sleep(0.1)

    # ``relax`` cancels any active gesture and returns the robot to a safe
    # resting state.
    controller.relax(True)

if __name__ == "__main__":
    main()
