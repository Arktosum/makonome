# memory/consolidator.py — weekly memory consolidation.
#
# Reads the period's raw episodic memories and distills them into one
# permanent summary memory (retrievable semantically like any other), and
# — only when the period revealed something durable — evolves about_siddhu.
#
# This is the slow lane of the two-speed identity design:
#   fast: current_context, updated by the curator every exchange
#   slow: about_siddhu, updated only here, only from weekly patterns
#
# Raw memories are never deleted; the summaries sit alongside them.

import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from config import CONSOLIDATION_PROMPT, CONSOLIDATION_MIN_MEMORIES, USER_NAME, TIMEZONE
from llm import complete
from memory.episodic import get_memories_since, save_memory
from memory.notes import get_note, write_note


def consolidate(since_iso: str) -> bool:
    """
    Run one consolidation pass over memories newer than since_iso.
    Returns True if a summary was produced, False if skipped.
    """
    t = time.time()

    rows = [r for r in get_memories_since(since_iso)
            if not r["content"].startswith("[week of")]  # never re-consolidate summaries
    if len(rows) < CONSOLIDATION_MIN_MEMORIES:
        print(f"🗜  Consolidation skipped — only {len(rows)} memories in period "
              f"(need {CONSOLIDATION_MIN_MEMORIES}+)", flush=True)
        return False

    memories_text = "\n".join(
        f"[{r.get('timestamp', '')[:10]}] {r['content']}" for r in rows
    )
    about = get_note("about_siddhu") or "(empty)"
    context = get_note("current_context") or "(unknown)"

    print(f"🗜  Consolidating {len(rows)} memories since {since_iso[:10]}...", flush=True)

    try:
        response = complete(
            messages=[
                {"role": "system", "content": CONSOLIDATION_PROMPT.format(user=USER_NAME)},
                {"role": "user", "content": f"""MEMORIES FROM THIS PERIOD:
{memories_text}

CURRENT ABOUT_SIDDHU:
{about}

CURRENT_CONTEXT:
{context}"""},
            ],
            role="consolidator",
        )
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
    except Exception as e:
        print(f"⚠️  Consolidation failed: {e}", flush=True)
        return False

    summary = (data.get("summary") or "").strip()
    if not summary:
        print("⚠️  Consolidation produced no summary — skipping", flush=True)
        return False

    week_label = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    save_memory("consolidation", f"[week of {week_label}] {summary}")
    print(f"🗜  Weekly summary saved: {summary[:80]}", flush=True)

    new_about = data.get("about_siddhu")
    if new_about and isinstance(new_about, str) and new_about.strip():
        # a shrunken identity document means the model dropped information
        if len(new_about) < len(about) * 0.6:
            print("⚠️  about_siddhu rewrite lost too much content — keeping the old one", flush=True)
        else:
            write_note("about_siddhu", new_about.strip(),
                       category="identity", auto_inject=True)
            print("🗜  about_siddhu evolved from this period's patterns", flush=True)

    print(f"⏱  consolidation: {time.time() - t:.2f}s", flush=True)
    return True
