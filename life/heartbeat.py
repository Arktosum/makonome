# life/heartbeat.py — Mako texting first, done responsibly.
#
# A scheduler thread ticks every N minutes but speaks rarely. Hard gates run
# BEFORE any LLM call:
#   quiet hours → min silence since you last talked → min gap since the last
#   heartbeat attempt → daily cap
# Only when every gate passes does the heartbeat model get asked "is there
# genuinely something worth saying?" — and SILENT is the expected answer.
#
# State persists in the _heartbeat_state note, so restarts don't reset the
# daily cap or re-ping. Every decision (including silence) is emitted to the
# dashboard activity feed. The same clock triggers the weekly reflection.

import json
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import HEARTBEAT, REFLECTION_EVERY_DAYS, HEARTBEAT_PROMPT, USER_NAME, TIMEZONE
from llm import complete
from memory.episodic import save_memory, get_last_memory_timestamp, get_recent_memory_rows
from memory.notes import get_note, write_note
from agent.events import emit

STATE_NOTE = "_heartbeat_state"


# ── persistent state ──────────────────────────────────────────

def _load_state() -> dict:
    try:
        raw = get_note(STATE_NOTE)
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _save_state(state: dict):
    write_note(STATE_NOTE, json.dumps(state), category="system")


# ── helpers ───────────────────────────────────────────────────

def _now():
    return datetime.now(ZoneInfo(TIMEZONE))


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            from datetime import timezone as _tz
            dt = dt.replace(tzinfo=_tz.utc)
        return dt.astimezone(ZoneInfo(TIMEZONE))
    except ValueError:
        return None


def _in_quiet_hours(now: datetime) -> bool:
    start, end = HEARTBEAT["quiet_start"], HEARTBEAT["quiet_end"]
    if start > end:  # wraps midnight, e.g. 23 → 8
        return now.hour >= start or now.hour < end
    return start <= now.hour < end


def _humanize(delta: timedelta) -> str:
    s = int(delta.total_seconds())
    if s < 3600:
        return f"{s // 60} minutes"
    if s < 86400:
        return f"{s // 3600} hours"
    return f"{s // 86400} days"


# ── the tick ──────────────────────────────────────────────────

def heartbeat_tick(session, force: bool = False) -> str:
    """
    One scheduler tick. Returns a short decision string (for logs/tests).
    `force` skips the hard gates (used for manual testing).
    """
    now = _now()
    state = _load_state()

    # reset the daily counter on date change
    today = now.strftime("%Y-%m-%d")
    if state.get("date") != today:
        state["date"] = today
        state["count_today"] = 0

    # ── reflection check rides the same clock ────────────
    _maybe_reflect(now, state)

    # ── hard gates (no LLM cost) ──────────────────────────
    if not force:
        if _in_quiet_hours(now):
            return "gate: quiet hours"

        last_talk = session.last_interaction or _parse_iso(get_last_memory_timestamp())
        last_hb = _parse_iso(state.get("last_heartbeat"))

        last_activity = max(d for d in (last_talk, last_hb, session.started) if d is not None)
        silence = now - last_activity

        if last_talk and (now - last_talk) < timedelta(hours=HEARTBEAT["min_silence_hours"]):
            return "gate: talked recently"
        if last_hb and (now - last_hb) < timedelta(hours=HEARTBEAT["min_gap_hours"]):
            return "gate: heartbeat gap"
        if state.get("count_today", 0) >= HEARTBEAT["daily_cap"]:
            return "gate: daily cap"
    else:
        last_talk = session.last_interaction or _parse_iso(get_last_memory_timestamp())
        silence = now - (last_talk or session.started)

    # ── the LLM decision ──────────────────────────────────
    decision = _decide(now, silence)

    state["last_heartbeat"] = now.isoformat()

    if decision is None:
        _save_state(state)
        emit({"type": "heartbeat", "data": {"decision": "silent"}})
        print("💓 Heartbeat: SILENT", flush=True)
        return "silent"

    # speak: dashboard message + session buffer + memory of having spoken
    state["count_today"] = state.get("count_today", 0) + 1
    _save_state(state)

    emit({"type": "heartbeat", "data": {"decision": "spoke", "message": decision}})
    emit({"type": "message", "data": {"role": "assistant", "content": decision}})
    session.note_assistant_message(decision)
    save_memory("assistant", f"(checked in unprompted) {decision}")

    # reach the phone even when no app is open
    from life.push import push
    push(decision, title="Mako 💚", tags="speech_balloon")

    print(f"💓 Heartbeat spoke: {decision}", flush=True)
    return f"spoke: {decision}"


def _decide(now: datetime, silence: timedelta) -> str | None:
    """Ask the heartbeat model whether there's something worth saying."""
    memories = get_recent_memory_rows(limit=6)
    memories_text = "\n".join(
        f"[{m.get('timestamp', '')[:10]}] {m['content'][:150]}" for m in memories
    ) or "(no memories)"

    prompt = HEARTBEAT_PROMPT.format(
        user=USER_NAME,
        time=now.strftime("%A, %B %d %Y, %I:%M %p"),
        silence=_humanize(silence),
        context=get_note("current_context") or "(unknown)",
        open_threads=get_note("open_threads") or "(nothing pending)",
        memories=memories_text,
    )

    try:
        response = complete(
            messages=[{"role": "system", "content": prompt},
                      {"role": "user", "content": "Decide now: SILENT, or your 1-2 sentence message."}],
            role="heartbeat",
        )
    except Exception as e:
        print(f"⚠️  Heartbeat LLM failed: {e}", flush=True)
        return None

    text = response.text.strip()
    if not text or "SILENT" in text.upper()[:20]:
        return None
    return text


def _maybe_reflect(now: datetime, state: dict):
    """Run the weekly self-reflection when it's due (and not at night)."""
    if _in_quiet_hours(now):
        return
    last = _parse_iso(state.get("last_reflection"))
    if last and (now - last) < timedelta(days=REFLECTION_EVERY_DAYS):
        return
    try:
        from life.reflection import reflect
        if reflect():
            state["last_reflection"] = now.isoformat()
            _save_state(state)
    except Exception as e:
        print(f"⚠️  Reflection failed: {e}", flush=True)


# ── the scheduler ─────────────────────────────────────────────

def start_heartbeat(session):
    def _loop():
        # let startup settle before the first tick
        time.sleep(60)
        while True:
            try:
                result = heartbeat_tick(session)
                if not result.startswith("gate"):
                    pass  # decision already logged/emitted
            except Exception as e:
                print(f"⚠️  Heartbeat tick failed: {e}", flush=True)
            time.sleep(HEARTBEAT["check_interval_min"] * 60)

    threading.Thread(target=_loop, daemon=True).start()
    print(f"💓 Heartbeat scheduler started (every {HEARTBEAT['check_interval_min']} min, "
          f"quiet {HEARTBEAT['quiet_start']}:00–{HEARTBEAT['quiet_end']}:00, "
          f"cap {HEARTBEAT['daily_cap']}/day)", flush=True)
