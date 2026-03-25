# wakeup.py — generates Mako's aware startup message
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from groq import Groq
from dotenv import load_dotenv
from config import GROQ_MODEL, WAKEUP_PROMPT, USER_NAME, ASSISTANT_NAME

load_dotenv()
_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _get_last_conversation_time() -> tuple[datetime | None, str]:
    """
    Query Supabase for the most recent memory timestamp.
    Returns (datetime, human_readable_string).
    """
    try:
        from memory import _get_client
        result = _get_client().table("memories") \
            .select("timestamp") \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()

        if not result.data:
            return None, "never — this seems to be our first conversation"

        last_ts = result.data[0]["timestamp"]
        # parse the timestamp
        last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        # make it timezone-naive for comparison
        last_dt_naive = last_dt.replace(tzinfo=None)
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        delta = now - last_dt_naive

        # human readable
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            readable = "just a moment ago"
        elif total_seconds < 3600:
            mins = total_seconds // 60
            readable = f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            readable = f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif total_seconds < 86400 * 2:
            readable = "yesterday"
        elif total_seconds < 86400 * 7:
            days = total_seconds // 86400
            readable = f"{days} days ago"
        elif total_seconds < 86400 * 30:
            weeks = total_seconds // (86400 * 7)
            readable = f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            months = total_seconds // (86400 * 30)
            readable = f"{months} month{'s' if months != 1 else ''} ago"

        return last_dt_naive, readable

    except Exception as e:
        print(f"⚠️  Could not get last conversation time: {e}", flush=True)
        return None, "unknown"


def _get_recent_memories() -> str:
    """Get the last few memories to give Mako context on wakeup."""
    try:
        from memory import _get_client
        result = _get_client().table("memories") \
            .select("role, content, timestamp") \
            .order("timestamp", desc=True) \
            .limit(6) \
            .execute()

        if not result.data:
            return "No memories yet."

        # reverse so chronological order
        rows = list(reversed(result.data))
        lines = []
        for row in rows:
            ts = row.get("timestamp", "")[:10]
            label = USER_NAME if row["role"] == "user" else ASSISTANT_NAME
            lines.append(f"[{ts}] {label}: {row['content'][:120]}")

        return "\n".join(lines)

    except Exception as e:
        print(f"⚠️  Could not get recent memories: {e}", flush=True)
        return "Could not retrieve memories."


def generate_wakeup_message() -> str:
    """
    Generate Mako's startup message with full time and memory context.
    Called once when Mako comes online.
    """
    print("💭 Generating wakeup message...", flush=True)

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.strftime("%A, %B %d %Y, %I:%M %p")
    _, last_seen = _get_last_conversation_time()
    recent_memories = _get_recent_memories()

    context = f"""Current time: {current_time}
Last conversation with {USER_NAME}: {last_seen}

Most recent memories:
{recent_memories}"""

    prompt = WAKEUP_PROMPT.format(user=USER_NAME)

    try:
        response = _groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": context}
            ],
            max_tokens=120,
            temperature=0.85,
        )
        message = response.choices[0].message.content.strip()
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
