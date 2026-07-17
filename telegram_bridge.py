# telegram_bridge.py — Mako in your pocket, properly.
#
# A Telegram bot bridge over the same Session as every other door:
#   - long-polls getUpdates in a daemon thread (no webhook, works anywhere)
#   - answers ONLY the owner (MAKO_TELEGRAM_CHAT_ID) — strangers get silence
#   - heartbeat check-ins arrive as real Telegram messages you can reply to
#
# Setup:
#   1. Telegram → @BotFather → /newbot → copy the token
#   2. .env / Render: MAKO_TELEGRAM_BOT_TOKEN=<token>
#   3. Message your bot once — the log prints your chat id
#   4. .env / Render: MAKO_TELEGRAM_CHAT_ID=<that id>
#
# No SDK — plain HTTPS via requests, ~zero dependencies.

import os
import threading
import time
import requests

_API = "https://api.telegram.org/bot{token}/{method}"
TELEGRAM_MAX_LEN = 4096


def _token() -> str | None:
    return os.environ.get("MAKO_TELEGRAM_BOT_TOKEN")


def _owner_chat_id() -> str | None:
    return os.environ.get("MAKO_TELEGRAM_CHAT_ID")


def is_configured() -> bool:
    return bool(_token() and _owner_chat_id())


def _call(method: str, timeout: int = 15, **params):
    token = _token()
    if not token:
        return None
    try:
        resp = requests.post(_API.format(token=token, method=method),
                             json=params, timeout=timeout)
        data = resp.json()
        return data.get("result") if data.get("ok") else None
    except Exception as e:
        print(f"⚠️  Telegram {method} failed: {e}", flush=True)
        return None


def chunk_text(text: str, limit: int = TELEGRAM_MAX_LEN) -> list[str]:
    """Split long replies at line boundaries where possible."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # single pathological line
            chunks.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def send_message(text: str, chat_id: str | None = None) -> bool:
    """Send a message to the owner (or an explicit chat). Used by push too."""
    chat_id = chat_id or _owner_chat_id()
    if not chat_id or not text:
        return False
    ok = True
    for chunk in chunk_text(text):
        # Mako writes *bold* — Telegram's legacy Markdown matches; fall back
        # to plain text if her formatting happens to break Telegram's parser
        result = _call("sendMessage", chat_id=chat_id, text=chunk,
                       parse_mode="Markdown")
        if result is None:
            result = _call("sendMessage", chat_id=chat_id, text=chunk)
        ok = ok and result is not None
    return ok


def handle_update(update: dict, think_fn) -> str | None:
    """Process one Telegram update. Returns the reply text sent (for tests)."""
    msg = update.get("message") or {}
    text = (msg.get("text") or "").strip()
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    if not text or not chat_id:
        return None

    owner = _owner_chat_id()
    if not owner:
        # setup mode: tell the sender their id, answer nothing else
        print(f"📨 Telegram message from chat id {chat_id} — set "
              f"MAKO_TELEGRAM_CHAT_ID={chat_id} to claim Mako", flush=True)
        send_message(f"Hi! To make me yours, set MAKO_TELEGRAM_CHAT_ID={chat_id} "
                     f"on my server and restart me.", chat_id=chat_id)
        return None
    if chat_id != owner:
        print(f"🚫 Ignored Telegram message from stranger chat {chat_id}", flush=True)
        return None

    _call("sendChatAction", chat_id=chat_id, action="typing")
    reply = think_fn(f"[from telegram] {text}")
    send_message(reply, chat_id=chat_id)
    return reply


def _poll_loop(think_fn):
    offset = 0
    print("📨 Telegram bridge polling...", flush=True)
    while True:
        try:
            updates = _call("getUpdates", timeout=60,
                            offset=offset, limit=10, allowed_updates=["message"])
            for u in (updates or []):
                offset = max(offset, u["update_id"] + 1)
                try:
                    handle_update(u, think_fn)
                except Exception as e:
                    print(f"⚠️  Telegram update failed: {e}", flush=True)
        except Exception as e:
            print(f"⚠️  Telegram poll error: {e}", flush=True)
            time.sleep(10)


def start_telegram(session):
    """Start the bridge if a bot token is configured; no-op otherwise."""
    if not _token():
        return
    me = _call("getMe")
    if not me:
        print("⚠️  Telegram token set but getMe failed — bridge not started", flush=True)
        return
    threading.Thread(target=_poll_loop, args=(session.think,), daemon=True).start()
    who = "owner set" if _owner_chat_id() else "NO OWNER YET — message the bot to get your chat id"
    print(f"📨 Telegram bridge online as @{me.get('username')} ({who})", flush=True)
