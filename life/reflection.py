# life/reflection.py — how Mako figures out who she is.
#
# Weekly, the reflection model reads Mako's journal (first-person lines the
# curator wrote after conversations) and rewrites about_mako from scratch.
# The seed personality in config.py never changes — but about_mako is loaded
# into every conversation, so the identity that actually talks to Siddhu is
# the accumulated one, drifting through lived experience.

from config import REFLECTION_PROMPT, USER_NAME
from llm import complete
from memory.episodic import get_recent_memory_rows
from memory.notes import get_note, write_note
from agent.events import emit


def reflect() -> bool:
    """
    Run one self-reflection pass. Returns True if about_mako was rewritten,
    False if skipped (no journal to reflect on yet).
    """
    journal = get_note("mako_journal")
    entries = [l for l in (journal or "").split("\n") if l.strip()]
    if len(entries) < 5:
        print(f"🪞 Reflection skipped — only {len(entries)} journal entries (need 5+)", flush=True)
        return False

    about_mako = get_note("about_mako") or "(no self-description yet — this is your first reflection)"
    memories = get_recent_memory_rows(limit=10)
    memories_text = "\n".join(
        f"[{m.get('timestamp', '')[:10]}] {m['content'][:150]}" for m in memories
    ) or "(none)"

    context = f"""CURRENT SELF-DESCRIPTION (about_mako):
{about_mako}

YOUR JOURNAL:
{journal}

RECENT MEMORIES:
{memories_text}"""

    print("🪞 Reflecting on who I'm becoming...", flush=True)
    response = complete(
        messages=[
            {"role": "system", "content": REFLECTION_PROMPT.format(user=USER_NAME)},
            {"role": "user",   "content": context},
        ],
        role="reflection",
    )

    new_identity = response.text.strip()
    if len(new_identity) < 50:
        print(f"⚠️  Reflection produced suspiciously short identity — keeping the old one", flush=True)
        return False

    write_note("about_mako", new_identity, category="identity", auto_inject=True)
    emit({"type": "heartbeat", "data": {"decision": "reflected",
                                        "message": "rewrote about_mako after reflecting on the journal"}})
    print("🪞 about_mako rewritten", flush=True)
    return True
