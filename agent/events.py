# agent/events.py — thread-safe event emission to the dashboard
from datetime import datetime
from zoneinfo import ZoneInfo
from config import TIMEZONE


def emit(event: dict):
    """Send an event to the dashboard via its thread-safe queue."""
    try:
        from dashboard.server import event_queue
        event.setdefault("time", datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S"))
        event_queue.put(event)
    except Exception as e:
        print(f"⚠️  Emit error: {e}", flush=True)
