from MovementControl import MovementControl


def main() -> None:
    """Simple hello world demonstrating MovementControl."""
    print("Hello!! (●'◡'●)")
    controller = MovementControl()
    controller.walk(1.0, 0.0, 0.0)
    controller.tick(0.1)


if __name__ == "__main__":
    main()
