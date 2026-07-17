# agent/session.py — one Session owns a conversation: buffer, context, loop.
# All frontends (dashboard, voice, CLI) talk to the same Session object.

import json
import threading
import time
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo
from config import BUFFER_TURNS, TIMEZONE, MEMORY_SEMANTIC_RESULTS, MEMORY_RECENT_RESULTS
from memory import retrieve_memories
from memory.curator import curate
from memory.notes import get_note, write_note
from agent.context import build_context
from agent.loop import run_agent_loop
from agent.events import emit

BUFFER_NOTE = "_session_buffer"


class Session:
    def __init__(self):
        self._buffer: deque[dict] = deque(maxlen=BUFFER_TURNS * 2)
        self._lock = threading.Lock()
        self._started = datetime.now(ZoneInfo(TIMEZONE))
        self.last_interaction: datetime | None = None
        self._restore_buffer()

    # ── buffer persistence — a redeploy must not wipe short-term memory ──
    def _restore_buffer(self):
        try:
            raw = get_note(BUFFER_NOTE)
            if raw:
                turns = json.loads(raw)
                self._buffer.extend(
                    t for t in turns
                    if isinstance(t, dict) and t.get("role") in ("user", "assistant")
                )
                if self._buffer:
                    print(f"🔁 Restored {len(self._buffer)} buffered turns", flush=True)
        except Exception as e:
            print(f"⚠️  Buffer restore failed: {e}", flush=True)

    def _persist_buffer(self):
        """Fire-and-forget save of the live buffer (called off the hot path)."""
        try:
            with self._lock:
                snapshot = list(self._buffer)
            write_note(BUFFER_NOTE, json.dumps(snapshot),
                       category="system", quiet=True)
        except Exception as e:
            print(f"⚠️  Buffer persist failed: {e}", flush=True)

    @property
    def started(self) -> datetime:
        return self._started

    def recent_transcript(self, turns: int = 10) -> str:
        """Plain-text tail of the live conversation (for the heartbeat's
        awareness of what was actually just said)."""
        with self._lock:
            tail = list(self._buffer)[-turns:]
        return "\n".join(
            f"{'Siddhu' if m['role'] == 'user' else 'Mako'}: {m['content'][:200]}"
            for m in tail
        )

    def note_assistant_message(self, content: str):
        """Record an unprompted assistant message (heartbeat) in the buffer,
        so a reply from the user lands in context."""
        with self._lock:
            self._buffer.append({"role": "assistant", "content": content})
        threading.Thread(target=self._persist_buffer, daemon=True).start()

    # ── session context ───────────────────────────────────────
    def session_context(self) -> str:
        s = int((datetime.now(ZoneInfo(TIMEZONE)) - self._started).total_seconds())
        if s < 60:
            return "just came online"
        if s < 3600:
            m = s // 60
            return f"online for {m} minute{'s' if m != 1 else ''}"
        return f"online for {s // 3600}h {(s % 3600) // 60}m"

    # ── main entry point ──────────────────────────────────────
    def think(self, user_message: str) -> str:
        # serialize turns — overlapping messages would interleave the buffer
        with self._lock:
            return self._think(user_message)

    def _think(self, user_message: str) -> str:
        t0 = time.time()
        print(f"\n{'─' * 50}", flush=True)
        print(f"🧠 think() called: {user_message[:60]}", flush=True)

        # 1. retrieve memories (semantic + recency split)
        t = time.time()
        memories = retrieve_memories(
            user_message,
            n_semantic=MEMORY_SEMANTIC_RESULTS,
            n_recent=MEMORY_RECENT_RESULTS,
        )
        print(f"⏱  memory retrieve: {time.time() - t:.2f}s", flush=True)
        if memories:
            emit({"type": "memory", "data": {"query": user_message[:60], "results": memories}})

        # 2. assemble context
        ctx = build_context(user_message, memories, self.session_context())

        # 3. build message array: system + real buffer turns + current message
        messages = [{"role": "system", "content": ctx["system"]}]
        messages.extend(self._buffer)
        messages.append({"role": "user", "content": ctx["user_content"]})

        # 4. prompt inspector breakdown
        buffer_text = "\n".join(
            f"{'user' if m['role'] == 'user' else 'mako'}: {m['content']}" for m in self._buffer
        )
        sections = ctx["sections"][:]
        sections.insert(-1, {"label": "BUFFER", "color": "amber", "text": buffer_text or "(empty)"})
        emit({"type": "prompt_debug", "data": {"user_message": user_message, "sections": sections}})
        emit({"type": "message", "data": {"role": "user", "content": user_message}})

        # 5. run the agentic loop
        answer = run_agent_loop(messages, ctx["tool_specs"])

        emit({"type": "message", "data": {"role": "assistant", "content": answer}})

        # 6. update buffer with the CLEAN turns (no volatile context block)
        self._buffer.append({"role": "user", "content": user_message})
        self._buffer.append({"role": "assistant", "content": answer})
        self.last_interaction = datetime.now(ZoneInfo(TIMEZONE))

        # 7. curator + buffer persistence run off the hot path
        threading.Thread(target=curate, args=(user_message, answer), daemon=True).start()
        threading.Thread(target=self._persist_buffer, daemon=True).start()

        print(f"⏱  TOTAL (excl. curator): {time.time() - t0:.2f}s", flush=True)
        print(f"{'─' * 50}\n", flush=True)
        return answer


# ── module-level singleton ────────────────────────────────────
_session: Session | None = None
_session_lock = threading.Lock()


def get_session() -> Session:
    global _session
    with _session_lock:
        if _session is None:
            _session = Session()
        return _session
