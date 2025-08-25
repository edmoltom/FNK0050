from MovementControl import MovementControl
import time


def main() -> None:
    """Simple hello world demonstrating MovementControl."""
    print("Hello!! (●'◡'●)")
    controller = MovementControl()
    controller.walk(1.0, 0.0, 0.0)

    for _ in range(20):
        controller.tick(0.1)
        time.sleep(0.1)

    controller.stop()


if __name__ == "__main__":
    main()
