# life/push.py — push notifications to Siddhu's phone.
#
# Backend: ntfy.sh — free, keyless pub/sub. The server publishes to a secret
# topic; the ntfy app on the phone subscribes to the same topic and delivers
# real push even when Mako's own app is closed.
#
# Setup: set MAKO_NTFY_TOPIC to a long random topic name (it's effectively a
# password — anyone who knows it can read pushes). Optionally MAKO_NTFY_SERVER
# for a self-hosted ntfy instance. If unset, push() is a silent no-op.
#
# Swap-in point for FCM later: keep the push() signature, change the guts.

import os
import requests

_NTFY_SERVER = os.environ.get("MAKO_NTFY_SERVER", "https://ntfy.sh").rstrip("/")


def is_configured() -> bool:
    return bool(os.environ.get("MAKO_NTFY_TOPIC"))


def push(message: str, title: str = "Mako", tags: str = "green_heart",
         priority: str = "default") -> bool:
    """
    Send a push notification. Returns True on success, False otherwise.
    Never raises — a failed push must never break the caller.
    """
    topic = os.environ.get("MAKO_NTFY_TOPIC")
    if not topic:
        return False
    try:
        resp = requests.post(
            f"{_NTFY_SERVER}/{topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": title.encode("utf-8"),
                "Tags": tags,
                "Priority": priority,
            },
            timeout=10,
        )
        ok = resp.status_code == 200
        print(f"{'📲 Push sent' if ok else f'⚠️  Push failed ({resp.status_code})'}: {message[:60]}", flush=True)
        return ok
    except Exception as e:
        print(f"⚠️  Push failed: {e}", flush=True)
        return False
