# main.py — Mako's entry point
import sys

# emoji-heavy logs must never crash on a cp1252 console
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

import os
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from config import ASSISTANT_NAME, USER_NAME, TIMEZONE
from agent import get_session
from dashboard.server import set_think_fn, start_server, event_queue

IS_CLOUD = os.environ.get("RENDER") is not None


def _emit_startup_message():
    from life.wakeup import generate_wakeup_message
    startup = generate_wakeup_message()
    event_queue.put({
        "type": "message",
        "time": datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S"),
        "data": {"role": "assistant", "content": startup},
    })
    return startup


def main():
    session = get_session()
    set_think_fn(session.think)

    startup = _emit_startup_message()

    from life.heartbeat import start_heartbeat
    start_heartbeat(session)

    from telegram_bridge import start_telegram
    start_telegram(session)

    if IS_CLOUD:
        print("☁️  Running in cloud mode", flush=True)
        # blocks forever — Flask handles everything
        start_server()
        return

    # ── Local mode ────────────────────────────────────────────
    threading.Thread(target=start_server, daemon=True).start()
    time.sleep(1)

    print(f"\n{'=' * 40}")
    print(f"  {ASSISTANT_NAME} is online.")
    print(f"{'=' * 40}\n")
    print(f"  Open http://localhost:8765 in your browser!")
    print(f"\n{ASSISTANT_NAME}: {startup}\n")
    print("  Waiting for input from dashboard... (Ctrl+C to quit, or type below)")

    # terminal input works too — same session as the dashboard
    while True:
        try:
            user_input = input().strip()
            if not user_input:
                continue
            if any(word in user_input.lower() for word in ["goodbye", "bye mako", "shut down", "exit"]):
                print(f"\n{ASSISTANT_NAME}: Okay, talk soon {USER_NAME}! I'll remember everything.\n")
                break
            response = session.think(user_input)
            print(f"\n{ASSISTANT_NAME}: {response}\n")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{ASSISTANT_NAME}: Shutting down. See you soon!\n")
            break


if __name__ == "__main__":
    print("Starting Mako...")
    main()
