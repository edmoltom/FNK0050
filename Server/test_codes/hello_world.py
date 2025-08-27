from MovementControl import MovementControl
import threading, time

def main() -> None:
    """Simple hello world demonstrating MovementControl."""
    print("Hello!! (●'◡'●)")
    controller = MovementControl()
    threading.Thread(target=controller.start_loop, daemon=True).start() 
    controller.gesture("greet") 
    time.sleep(10)  
    controller.relax()

if __name__ == "__main__":
    main()
