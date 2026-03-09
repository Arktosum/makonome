# main.py
import threading
import time
from datetime import datetime
from brain import think
from config import SYSTEM_PROMPT, USER_NAME
from voice.mouth import speak
from dashboard.server import set_think_fn, start_server, event_queue
from heartbeat import start_heartbeat, update_activity
import json


def start_dashboard_server():
    from dashboard.server import start_server
    start_server()


def get_input(voice_mode: bool) -> str:
    if voice_mode:
        from voice.ears import listen
        return listen()
    else:
        return input(f"{USER_NAME}: ").strip()


def on_heartbeat_message(text: str):
    """Called by heartbeat when Mako wants to say something unprompted."""
    # emit to dashboard as a chat bubble
    event_queue.put({
        "type": "message",
        "time": datetime.now().strftime("%H:%M:%S"),
        "data": {"role": "assistant", "content": text}
    })
    # speak it out loud
    try:
        speak(text)
    except Exception as e:
        print(f"💓 TTS error: {e}", flush=True)

    # save to memory so Mako remembers she said this
    from memory import save_memory
    save_memory("assistant", f"[unprompted] {text}")


def main():
    # register think function with dashboard
    set_think_fn(think)

    # start dashboard server
    thread = threading.Thread(target=start_dashboard_server, daemon=True)
    thread.start()

    # small delay to let server start
    time.sleep(1)

    print(f"\n{'='*40}")
    print(f"  {SYSTEM_PROMPT} is online.")
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

    # start heartbeat
    start_heartbeat(on_heartbeat_message)
    print(f"💓 Heartbeat active — Mako will check in on you randomly", flush=True)

    startup = f"Hey {USER_NAME}! I'm here. What's up?"
    print(f"{SYSTEM_PROMPT}: {startup}")

    if voice_output:
        speak(startup)

    # emit startup to dashboard
    event_queue.put({
        "type": "message",
        "time": datetime.now().strftime("%H:%M:%S"),
        "data": {"role": "assistant", "content": startup}
    })

    if dashboard_mode:
        print("  Waiting for input from dashboard...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{SYSTEM_PROMPT}: Shutting down. See you soon!\n")
        return

    while True:
        try:
            user_input = get_input(voice_mode)
            if not user_input:
                continue

            # update activity timestamp so heartbeat knows you're here
            update_activity()

            if any(word in user_input.lower() for word in ["goodbye", "bye mako", "shut down", "exit"]):
                farewell = f"Okay, talk soon {USER_NAME}! I'll remember everything."
                print(f"\n{SYSTEM_PROMPT}: {farewell}\n")
                if voice_output:
                    speak(farewell)
                break

            if not voice_mode:
                print(f"\n{USER_NAME}: {user_input}")

            response = think(user_input)

            # update activity after response too
            update_activity()

            print(f"\n{SYSTEM_PROMPT}: {response}\n")
            if voice_output:
                speak(response)

        except KeyboardInterrupt:
            print(f"\n\n{SYSTEM_PROMPT}: Shutting down. See you soon!\n")
            break


if __name__ == "__main__":
    print("Starting Mako...")
    main()
