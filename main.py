# main.py
import os
import threading
import time
from datetime import datetime
from brain import think
from config import ASSISTANT_NAME, USER_NAME
from dashboard.server import set_think_fn, start_server, event_queue
from heartbeat import start_heartbeat, update_activity

# ── Environment detection ─────────────────────────────────────────────────────
IS_CLOUD = os.environ.get("RENDER") is not None


def on_heartbeat_message(text: str):
    """Called by heartbeat when Mako wants to say something unprompted."""
    event_queue.put({
        "type": "message",
        "time": datetime.now().strftime("%H:%M:%S"),
        "data": {"role": "assistant", "content": text}
    })

    # speak locally only
    if not IS_CLOUD:
        try:
            from voice.mouth import speak
            speak(text)
        except Exception as e:
            print(f"💓 TTS error: {e}", flush=True)

    from memory import save_memory
    save_memory("assistant", f"[unprompted] {text}")


def main():
    # register think function with dashboard
    set_think_fn(think)

    # start heartbeat
    start_heartbeat(on_heartbeat_message)
    print(f"💓 Heartbeat active", flush=True)

    # emit startup message
    startup = f"Hey {USER_NAME}! I'm here. What's up?"
    event_queue.put({
        "type": "message",
        "time": datetime.now().strftime("%H:%M:%S"),
        "data": {"role": "assistant", "content": startup}
    })

    if IS_CLOUD:
        # ── Cloud mode ────────────────────────────────────────
        print(f"☁️  Running in cloud mode — dashboard only", flush=True)
        print(f"\n{'='*40}")
        print(f"  {ASSISTANT_NAME} is online.")
        print(f"{'='*40}\n")
        # start_server blocks forever — that's our entire main loop
        start_server()

    else:
        # ── Local mode ────────────────────────────────────────
        from voice.mouth import speak

        # start dashboard in background thread
        threading.Thread(target=start_server, daemon=True).start()
        time.sleep(1)

        print(f"\n{'='*40}")
        print(f"  {ASSISTANT_NAME} is online.")
        print(f"{'='*40}\n")

        print("Input mode:")
        print("  [1] Voice (microphone)")
        print("  [2] Text (terminal)")
        print("  [3] Dashboard only (browser at http://localhost:8765)")
        choice = input("Choose (1/2/3): ").strip()
        voice_mode = choice == "1"
        dashboard_mode = choice == "3"

        if not dashboard_mode:
            print("\nOutput mode:")
            print("  [1] Voice + Text")
            print("  [2] Text only")
            voice_output = input("Choose (1/2): ").strip() == "1"
        else:
            voice_output = False
            print(f"\n  Open http://localhost:8765 in your browser!")

        print(f"\n{'='*40}\n")
        print(f"{ASSISTANT_NAME}: {startup}")
        if voice_output:
            speak(startup)

        if dashboard_mode:
            print("  Waiting for input from dashboard...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print(f"\n{ASSISTANT_NAME}: Shutting down. See you soon!\n")
            return

        while True:
            try:
                if voice_mode:
                    from voice.ears import listen
                    user_input = listen()
                else:
                    user_input = input(f"{USER_NAME}: ").strip()

                if not user_input:
                    continue

                update_activity()

                if any(word in user_input.lower() for word in ["goodbye", "bye mako", "shut down", "exit"]):
                    farewell = f"Okay, talk soon {USER_NAME}! I'll remember everything."
                    print(f"\n{ASSISTANT_NAME}: {farewell}\n")
                    if voice_output:
                        speak(farewell)
                    break

                if not voice_mode:
                    print(f"\n{USER_NAME}: {user_input}")

                response = think(user_input)
                update_activity()

                print(f"\n{ASSISTANT_NAME}: {response}\n")
                if voice_output:
                    speak(response)

            except KeyboardInterrupt:
                print(f"\n\n{ASSISTANT_NAME}: Shutting down. See you soon!\n")
                break


if __name__ == "__main__":
    print("Starting Mako...")
    main()
