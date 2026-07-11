# life/wakeup.py — generates Mako's aware startup message
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from config import WAKEUP_PROMPT, USER_NAME, ASSISTANT_NAME, TIMEZONE
from llm import complete
from memory.episodic import get_last_memory_timestamp, get_recent_memory_rows


def _humanize_silence() -> str:
    """How long since the last conversation, as a human-readable string."""
    last_ts = get_last_memory_timestamp()
    if last_ts is None:
        return "never — this seems to be our first conversation"

    try:
        last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            # stored without offset — assume UTC
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - last_dt
    except ValueError:
        return "unknown"

    s = int(delta.total_seconds())
    if s < 60:
        return "just a moment ago"
    if s < 3600:
        m = s // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if s < 86400:
        h = s // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    if s < 86400 * 2:
        return "yesterday"
    if s < 86400 * 7:
        return f"{s // 86400} days ago"
    if s < 86400 * 30:
        w = s // (86400 * 7)
        return f"{w} week{'s' if w != 1 else ''} ago"
    mo = s // (86400 * 30)
    return f"{mo} month{'s' if mo != 1 else ''} ago"


def _recent_memories_text() -> str:
    rows = get_recent_memory_rows(limit=6)
    if not rows:
        return "No memories yet."
    lines = []
    for row in rows:
        ts = row.get("timestamp", "")[:10]
        label = USER_NAME if row["role"] == "user" else ASSISTANT_NAME
        lines.append(f"[{ts}] {label}: {row['content'][:120]}")
    return "\n".join(lines)


def generate_wakeup_message() -> str:
    """
    Generate Mako's startup message with full time and memory context.
    Called once when Mako comes online.
    """
    print("💭 Generating wakeup message...", flush=True)

    now = datetime.now(ZoneInfo(TIMEZONE))
    current_time = now.strftime("%A, %B %d %Y, %I:%M %p")

    context = f"""Current time: {current_time}
Last conversation with {USER_NAME}: {_humanize_silence()}

Most recent memories:
{_recent_memories_text()}"""

    try:
        response = complete(
            messages=[
                {"role": "system", "content": WAKEUP_PROMPT.format(user=USER_NAME)},
                {"role": "user",   "content": context},
            ],
            role="wakeup",
            max_tokens=120,
            temperature=0.85,
        )
        message = response.text.strip()
        print(f"✅ Wakeup message: {message}", flush=True)
        return message

    except Exception as e:
        print(f"⚠️  Wakeup generation failed: {e}", flush=True)
        # fallback — at least time-aware
        hour = now.hour
        if hour < 12:
            return f"Morning, {USER_NAME}."
        elif hour < 17:
            return f"Hey {USER_NAME}, I'm back."
        elif hour < 21:
            return f"Evening, {USER_NAME}."
        else:
            return f"Hey, you're up late {USER_NAME}."
