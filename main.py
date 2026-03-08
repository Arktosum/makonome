# main.py
import threading
import asyncio
from brain import think
from config import ASSISTANT_NAME, USER_NAME
from voice.mouth import speak
from dashboard.server import set_think_fn, start_server, event_queue
import json
from datetime import datetime


def start_dashboard_server():
    from dashboard.server import start_server
    start_server()


def get_input(voice_mode: bool) -> str:
    if voice_mode:
        from voice.ears import listen
        return listen()
    else:
        return input(f"{USER_NAME}: ").strip()


def main():
    # register think function with dashboard so browser can trigger it
    set_think_fn(think)

    # start dashboard server in background
    thread = threading.Thread(target=start_dashboard_server, daemon=True)
    thread.start()

    print(f"\n{'='*40}")
    print(f"  {ASSISTANT_NAME} is online.")
    print(f"{'='*40}\n")

    print("Input mode:")
    print("  [1] Voice (microphone)")
    print("  [2] Text (terminal)")
    print("  [3] Dashboard (browser at http://localhost:8765)")
    choice = input("Choose (1/2/3): ").strip()
    voice_mode = choice == "1"
    dashboard_mode = choice == "3"

    if not dashboard_mode:
        print("\nOutput mode:")
        print("  [1] Voice + Text")
        print("  [2] Text only")
        choice2 = input("Choose (1/2): ").strip()
        voice_output = choice2 == "1"
    else:
        voice_output = False
        print(f"\n  Open http://localhost:8765 in your browser!")

    print(f"\n{'='*40}\n")

    startup = f"Hey {USER_NAME}! I'm here. What's up?"
    print(f"{ASSISTANT_NAME}: {startup}")
    if voice_output:
        speak(startup)

    # emit startup message to dashboard
    event_queue.put({
        "type": "message",
        "time": datetime.now().strftime("%H:%M:%S"),
        "data": {"role": "assistant", "content": startup}
    })

    if dashboard_mode:
        # just keep alive, dashboard handles all input
        print("  Waiting for input from dashboard...")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{ASSISTANT_NAME}: Shutting down. See you soon!\n")
        return

    while True:
        try:
            user_input = get_input(voice_mode)
            if not user_input:
                continue

            if any(word in user_input.lower() for word in ["goodbye", "bye mako", "shut down", "exit"]):
                farewell = f"Okay, talk soon {USER_NAME}! I'll remember everything."
                print(f"\n{ASSISTANT_NAME}: {farewell}\n")
                if voice_output:
                    speak(farewell)
                break

            if not voice_mode:
                print(f"\n{USER_NAME}: {user_input}")

            response = think(user_input)
            print(f"\n{ASSISTANT_NAME}: {response}\n")
            if voice_output:
                speak(response)

        except KeyboardInterrupt:
            print(f"\n\n{ASSISTANT_NAME}: Shutting down. See you soon!\n")
            break


if __name__ == "__main__":
    main()
