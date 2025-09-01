from .application import Application


def main() -> None:
    """Entry point for running the application as a module."""
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
