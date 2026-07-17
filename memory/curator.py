# memory/curator.py — background reflection after each exchange.
# Decides what's worth remembering, which notes need updating, routes facts
# about people to their person_ notes, keeps open_threads current, and writes
# Mako's first-person journal.
#
# IMPORTANT: the curator always sees the FULL content of notes it may rewrite.
# Feeding it truncated notes while asking for complete rewrites silently
# destroys everything past the truncation point.

import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from config import USER_NAME, TIMEZONE
from llm import complete
from memory.episodic import save_memory
from memory.notes import get_note, write_note, append_note, get_notes_by_category

# notes that are always loaded into Mako's context — updates to these
# keep the auto_inject flag
AUTO_INJECT_NOTES = ("about_siddhu", "about_mako", "current_context", "open_threads")

_ANALYSIS_PROMPT = f"""You are Mako's memory curator. Analyze one conversation exchange
and decide what to update in Mako's knowledge base.

The knowledge base:
- about_siddhu: permanent identity document about {USER_NAME}
  (do NOT update this — a weekly consolidation process owns it; durable identity
  changes emerge from patterns, not single exchanges)
- about_mako: Mako's own identity (do NOT update this — a separate reflection process owns it)
- current_context: what's happening in {USER_NAME}'s life right now — THIS is
  where fresh life updates go (new events, current situations, what's on his plate)
- open_threads: pending things worth following up on later
- person_<name>: one note per person in {USER_NAME}'s life (person_gayathri, person_amma, ...)
- project_<name> / topic notes: deeper notes on projects and topics

Respond in JSON only:
{{
  "save_memory": true or false,
  "memory": "concise episodic memory worth saving (or null)",
  "importance": 1-10 — how much this memory should outlast time. 1-3: trivia,
                small talk. 4-6: everyday life worth recalling. 7-8: real events,
                decisions, feelings that matter. 9-10: life milestones.,
  "journal": "ONE first-person line in Mako's voice about this exchange — an observation,
              a feeling, something learned about {USER_NAME} or about herself (or null
              if the exchange was too trivial to journal)",
  "updates": [
    {{
      "note": "note_name",
      "action": "update|create",
      "reason": "why this note needs updating",
      "new_content": "the COMPLETE new content of the note (full rewrite, not just the change)"
    }}
  ]
}}

Rules:
- Only update notes if something genuinely new or conflicting was learned
- When updating, always rewrite the COMPLETE note — never partial patches,
  and never drop existing information that is still true
- If new info contradicts existing info, the new info wins
- PEOPLE: when {USER_NAME} mentions someone in his life, route facts to that
  person's person_<firstname> note. First line of every person note MUST be:
  "> Name — one-line relationship summary" (used as an index). Then markdown
  sections: who they are, key facts, recent events, open threads with them.
- OPEN_THREADS: a markdown checklist of pending things with expected dates when
  known ("- [ ] Gayathri's exam results — due around July 15"). Add new pending
  things; REMOVE threads that got resolved in this exchange. If nothing is
  pending, content is exactly "(nothing pending)".
- save_memory=false for small talk, weather queries, ephemeral info
- The journal is Mako's inner voice — candid, specific, first person, one line
- Max 3 updates per exchange
- Keep note content clean, structured markdown
"""


def _category_for(note_name: str) -> str:
    if note_name.startswith("about_"):
        return "identity"
    if note_name in ("current_context", "open_threads"):
        return "context"
    if note_name.startswith("person_"):
        return "person"
    if note_name.startswith("project_"):
        return "project"
    return "general"


def _people_block(exchange_text: str) -> str:
    """
    Person notes context: full content for anyone mentioned in the exchange
    (so rewrites never lose data), names only for everyone else.
    """
    people = get_notes_by_category("person")
    if not people:
        return "(no person notes yet)"

    lower = exchange_text.lower()
    mentioned, others = [], []
    for p in people:
        first_name = p["name"].removeprefix("person_").replace("_", " ")
        if first_name and first_name in lower:
            mentioned.append(f"=== {p['name'].upper()} ===\n{p['content']}")
        else:
            others.append(p["name"])

    parts = mentioned[:]
    if others:
        parts.append("Other person notes (not shown): " + ", ".join(others))
    return "\n\n".join(parts)


def curate(user_message: str, assistant_message: str):
    """
    Background analysis after each exchange.
    Updates notes, writes the journal, and saves episodic memory if warranted.
    """
    t = time.time()

    try:
        exchange = f"{USER_NAME}: {user_message}\nMako: {assistant_message}"

        # full note contents — never truncated (see module docstring)
        context_block = f"""CURRENT NOTES:

=== ABOUT_SIDDHU ===
{get_note("about_siddhu") or "(empty)"}

=== CURRENT_CONTEXT ===
{get_note("current_context") or "(empty)"}

=== OPEN_THREADS ===
{get_note("open_threads") or "(nothing pending)"}

=== PEOPLE ===
{_people_block(exchange)}

EXCHANGE:
{exchange}"""

        response = complete(
            messages=[
                {"role": "system", "content": _ANALYSIS_PROMPT},
                {"role": "user",   "content": context_block},
            ],
            role="curator",
        )

        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(text)

        # episodic memory — importance-tagged, deduped at write time
        if data.get("save_memory") and data.get("memory"):
            importance = data.get("importance") or 5
            if save_memory("user", data["memory"], importance=importance, dedupe=True):
                print(f"🧠 Memory saved [!{importance}]: {data['memory'][:80]}", flush=True)

        # Mako's journal — her inner voice, feeds the weekly reflection
        if data.get("journal"):
            today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
            append_note("mako_journal", f"[{today}] {data['journal']}", category="journal")
            print(f"📔 Journal: {data['journal'][:80]}", flush=True)

        # note updates
        for update in data.get("updates", []):
            note_name = update.get("note", "")
            action    = update.get("action", "update")
            content   = update.get("new_content", "")
            reason    = update.get("reason", "")

            if not note_name or not content:
                continue
            if note_name in ("about_mako", "about_siddhu"):
                # reflection owns Mako's identity; weekly consolidation owns
                # Siddhu's — the curator only touches the fast layers
                continue

            # rewrite safety: full-rewrite semantics are lossy by nature,
            # so guard every overwrite of an existing note
            old = get_note(note_name)
            if old is not None:
                if content.strip() == old.strip():
                    continue  # nothing actually changed — skip the churn
                # fast-layer notes (threads resolve, context moves on) may
                # legitimately shrink; knowledge notes must not
                shrinkable = note_name in ("open_threads", "current_context")
                if not shrinkable and len(old) > 300 and len(content) < len(old) * 0.6:
                    print(f"⚠️  Rejected lossy rewrite of [{note_name}] "
                          f"({len(old)} → {len(content)} chars)", flush=True)
                    continue
                # one-version undo: stash what's being replaced
                write_note(f"_backup_{note_name}", old, category="system")

            write_note(
                note_name, content,
                category=_category_for(note_name),
                auto_inject=note_name in AUTO_INJECT_NOTES,
            )
            print(f"{'📝' if action == 'update' else '✨'} Note {action}d [{note_name}]: {reason[:60]}", flush=True)

    except Exception as e:
        print(f"⚠️  Post-analysis failed ({e}), saving raw memory", flush=True)
        save_memory("user", user_message)
        save_memory("assistant", assistant_message)

    print(f"⏱  curator: {time.time() - t:.2f}s", flush=True)
