# heartbeat.py
import os
import threading
import random
import time
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from config import GROQ_MODEL, SYSTEM_PROMPT, ASSISTANT_NAME, USER_NAME

load_dotenv()
_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

# how long since last conversation before Mako considers speaking
MIN_SILENCE_MINUTES = 10   # won't interrupt if you just talked
MAX_SILENCE_MINUTES = 30   # won't go longer than this without checking in

# track last conversation time so we don't interrupt mid-chat
_last_activity = datetime.now()
_lock = threading.Lock()


def update_activity():
    """Call this whenever user or Mako sends a message."""
    global _last_activity
    with _lock:
        _last_activity = datetime.now()


def _minutes_since_activity():
    with _lock:
        delta = datetime.now() - _last_activity
        return delta.total_seconds() / 60


HEARTBEAT_PROMPT = """
You are Mako, checking in on {user} unprompted like a real friend would.

Current time: {time}

Relevant memories about {user}:
{memories}

Your job: decide if you have something genuine and natural to say right now.
Think about:
- The time of day (morning greeting, evening check-in, late night concern)
- Something from your memories worth following up on
- A friendly observation or thought
- A reminder about something they mentioned

Rules:
- If you have something worth saying, respond naturally in 1-2 sentences max
- Sound like a real friend, not an assistant
- NEVER say "I noticed you haven't talked to me" or anything that sounds needy
- NEVER make up fake memories or events
- If you genuinely have nothing worth saying right now, respond with exactly: SILENT
- Be SILENT more often than not — only speak when it feels truly natural
"""


def _should_speak() -> str | None:
    """
    Ask the LLM if Mako has something worth saying.
    Returns the message string, or None if she should stay quiet.
    """
    from memory import retrieve_memories

    current_time = datetime.now().strftime("%A, %B %d %Y, %I:%M %p")

    query = f"time of day {datetime.now().strftime('%H:%M')} {USER_NAME} recent activities"
    memories = retrieve_memories(query)
    memory_block = "\n".join(
        memories) if memories else "No specific memories yet."

    prompt = HEARTBEAT_PROMPT.format(
        user=USER_NAME,
        time=current_time,
        memories=memory_block
    )

    try:
        response = _groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": "Do you have something to say?"}
            ],
            max_tokens=128,
            temperature=0.8,
        )
        message = response.choices[0].message.content.strip()

        if message.upper() == "SILENT" or "SILENT" in message.upper()[:10]:
            return None

        return message

    except Exception as e:
        print(f"💓 Heartbeat error: {e}", flush=True)
        return None


def _heartbeat_loop(on_message):
    """
    Main heartbeat loop. Runs forever in background.
    Calls on_message(text) when Mako decides to speak.
    """
    print(f"💓 Heartbeat started", flush=True)

    while True:
        sleep_minutes = random.uniform(
            MIN_SILENCE_MINUTES, MAX_SILENCE_MINUTES)
        print(
            f"💓 Next heartbeat check in {sleep_minutes:.1f} minutes", flush=True)
        time.sleep(sleep_minutes * 60)

        silence = _minutes_since_activity()
        if silence < MIN_SILENCE_MINUTES:
            print(
                f"💓 Too soon since last activity ({silence:.1f} min), skipping", flush=True)
            continue

        print(f"💓 Checking if Mako has something to say...", flush=True)
        message = _should_speak()

        if message:
            print(f"💓 Mako speaks: {message}", flush=True)
            update_activity()
            on_message(message)
        else:
            print(f"💓 Mako stays quiet", flush=True)


def start_heartbeat(on_message):
    """
    Start the heartbeat in a background thread.
    on_message(text) is called whenever Mako decides to speak.
    """
    thread = threading.Thread(
        target=_heartbeat_loop,
        args=(on_message,),
        daemon=True
    )
    thread.start()
    return thread
