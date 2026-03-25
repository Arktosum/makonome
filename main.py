# main.py
import os
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from brain import think
from config import ASSISTANT_NAME, USER_NAME
from dashboard.server import set_think_fn, start_server, event_queue

# ── Environment detection ─────────────────────────────────────────────────────
IS_CLOUD = os.environ.get("RENDER") is not None


def main():
    # register think function with dashboard
    set_think_fn(think)

    # generate aware wakeup message
    from wakeup import generate_wakeup_message
    startup = generate_wakeup_message()
    event_queue.put({
        "type": "message",
        "time": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
        "data": {"role": "assistant", "content": startup}
    })

    if IS_CLOUD:
        print("☁️  Running in cloud mode", flush=True)
        set_think_fn(think)
        # emit startup message
        event_queue.put({
            "type": "message",
            "time": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
            "data": {"role": "assistant", "content": startup}
        })
        # this blocks forever — Flask handles everything
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

        # default to dashboard mode locally — change to "1" or "2" for voice/text
        voice_mode = False
        dashboard_mode = True
        voice_output = False
        print(f"  Open http://localhost:8765 in your browser!")

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
    print("Starting Mako...")
    main()


