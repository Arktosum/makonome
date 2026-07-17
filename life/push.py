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
    from telegram_bridge import is_configured as tg_configured
    return bool(os.environ.get("MAKO_NTFY_TOPIC")) or tg_configured()


def push(message: str, title: str = "Mako", tags: str = "green_heart",
         priority: str = "default") -> bool:
    """
    Send a push notification through every configured channel.
    Telegram is preferred (the notification is a real chat you can reply to);
    ntfy fires alongside if set. Never raises — a failed push must never
    break the caller. Returns True if any channel delivered.
    """
    delivered = False
    try:
        from telegram_bridge import is_configured as tg_configured, send_message
        if tg_configured() and send_message(message):
            print(f"📨 Telegram push sent: {message[:60]}", flush=True)
            delivered = True
    except Exception as e:
        print(f"⚠️  Telegram push failed: {e}", flush=True)
    return _push_ntfy(message, title, tags, priority) or delivered


def _push_ntfy(message: str, title: str, tags: str, priority: str) -> bool:
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
