# agent/context.py — assembles Mako's context for each message.
#
# Layering (cache-friendly: stable stuff first, volatile stuff last):
#   system prompt  = personality seed + [ReAct tools, if fallback] + identity notes
#   buffer         = real user/assistant message turns (not string-stuffed)
#   user message   = volatile block (time, session, topic notes, memories) + text
#
# Also produces the section breakdown for the dashboard's prompt inspector.

from datetime import datetime
from zoneinfo import ZoneInfo
from config import SYSTEM_PROMPT, TIMEZONE
from llm.client import route_supports_native_tools
from llm.react_fallback import build_react_prompt
from memory import get_auto_inject_notes, get_relevant_notes
from memory.notes import get_notes_by_category, get_note_index
from tools.registry import get_specs

_DIV = "=" * 50


def _section(title: str, body: str) -> str:
    return f"\n\n{_DIV}\n{title}\n{_DIV}\n{body}"


def _build_people_index() -> str:
    """One line per person note: the '> Name — relationship' summary line."""
    people = get_notes_by_category("person")
    lines = []
    for p in people:
        first_line = (p["content"] or "").split("\n", 1)[0].strip()
        if first_line.startswith(">"):
            lines.append(first_line.lstrip("> ").strip() + f"  [{p['name']}]")
        else:
            lines.append(f"{p['name'].removeprefix('person_').replace('_', ' ').title()}  [{p['name']}]")
    return "\n".join(lines)


def build_context(user_message: str, memories: list[str], session_ctx: str) -> dict:
    """
    Returns:
      system        — the system prompt string
      user_content  — the current user turn (volatile context + message)
      sections      — inspector breakdown [{label, color, text}]
      tool_specs    — native tool specs, or None when on the ReAct fallback
    """
    native = route_supports_native_tools("chat")
    specs = get_specs()

    tools_text = "(native tool calling — schemas passed via API)" if native \
        else build_react_prompt(specs)

    system = SYSTEM_PROMPT
    if not native:
        system += tools_text

    identity_block = get_auto_inject_notes()
    if identity_block:
        system += _section("IDENTITY & CONTEXT", identity_block)

    # people index — who exists in the user's world, one line each.
    # Full person notes load on demand (keyword match or read_note).
    people_index = _build_people_index()
    if people_index:
        system += _section(
            "PEOPLE IN HIS LIFE",
            people_index + "\n(use read_note on a person_ note for full details)",
        )

    # note index — what she keeps notes about, so she can read_note on demand
    note_index = get_note_index()
    if note_index:
        system += _section(
            "YOUR NOTES",
            note_index + "\n(use read_note when one is relevant to the conversation)",
        )

    # ── volatile block, attached to the current user turn ─────
    current_time = datetime.now(ZoneInfo(TIMEZONE)).strftime("%A, %B %d %Y, %I:%M %p")

    volatile = f"Current time: {current_time}\nSession: {session_ctx}"

    relevant_notes = get_relevant_notes(user_message)
    if relevant_notes:
        notes_block = "\n\n".join(f"=== {n['name'].upper()} ===\n{n['content']}" for n in relevant_notes)
        volatile += f"\n\nRELEVANT NOTES:\n{notes_block}"
        print(f"   📎 Injected {len(relevant_notes)} topic note(s)", flush=True)

    if memories:
        volatile += "\n\nRELEVANT MEMORIES:\n" + "\n".join(memories)

    user_content = f"[context]\n{volatile}\n[/context]\n\n{user_message}"

    sections = [
        {"label": "PERSONALITY",   "color": "blue",   "text": SYSTEM_PROMPT},
        {"label": "TOOLS",         "color": "purple", "text": tools_text},
        {"label": "IDENTITY & NOTES", "color": "green", "text": identity_block or "(none yet)"},
        {"label": "PEOPLE",        "color": "purple", "text": people_index or "(no person notes yet)"},
        {"label": "NOTE INDEX",    "color": "green",  "text": note_index or "(no topic notes yet)"},
        {"label": "TOPIC NOTES",   "color": "amber",  "text": "\n\n".join(f"[{n['name']}]\n{n['content']}" for n in relevant_notes) or "(none relevant)"},
        {"label": "MEMORIES",      "color": "cyan",   "text": "\n".join(memories) or "(none retrieved)"},
        {"label": "USER MESSAGE",  "color": "red",    "text": f"[{current_time}]\n{user_message}"},
    ]

    return {
        "system": system,
        "user_content": user_content,
        "sections": sections,
        "tool_specs": specs if native else None,
    }
