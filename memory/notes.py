# memory/notes.py — Mako's structured knowledge base (identity, people, projects)
from datetime import datetime
from zoneinfo import ZoneInfo
from config import TIMEZONE
from memory.db import get_client


def get_auto_inject_notes() -> str:
    """
    Retrieve all notes marked auto_inject=true.
    These are always included in every system prompt.
    Returns formatted string ready to inject.
    """
    try:
        result = get_client().table("notes") \
            .select("name, content") \
            .eq("auto_inject", True) \
            .order("name") \
            .execute()

        if not result.data:
            return ""

        sections = []
        for row in result.data:
            sections.append(f"=== {row['name'].upper().replace('_', ' ')} ===\n{row['content']}")

        return "\n\n".join(sections)

    except Exception as e:
        print(f"⚠️  Auto-inject notes failed: {e}", flush=True)
        return ""


def get_note(name: str) -> str | None:
    """Read a specific note by name. Returns content or None if not found."""
    try:
        result = get_client().table("notes") \
            .select("content") \
            .eq("name", name) \
            .limit(1) \
            .execute()

        if result.data:
            return result.data[0]["content"]
        return None

    except Exception as e:
        print(f"⚠️  Get note failed: {e}", flush=True)
        return None


def write_note(name: str, content: str, category: str = "general",
               auto_inject: bool = False, quiet: bool = False):
    """Create or fully overwrite a note."""
    try:
        sb = get_client()

        existing = sb.table("notes") \
            .select("id") \
            .eq("name", name) \
            .limit(1) \
            .execute()

        if existing.data:
            sb.table("notes").update({
                "content":    content,
                "updated_at": datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
            }).eq("name", name).execute()
            if not quiet:
                print(f"📝 Note updated: {name}", flush=True)
        else:
            sb.table("notes").insert({
                "name":        name,
                "content":     content,
                "category":    category,
                "auto_inject": auto_inject,
                "updated_at":  datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
            }).execute()
            if not quiet:
                print(f"📝 Note created: {name}", flush=True)

    except Exception as e:
        print(f"⚠️  Write note failed: {e}", flush=True)


def list_notes() -> list[str]:
    """Return list of all note names Mako can access."""
    try:
        result = get_client().table("notes") \
            .select("name, category, auto_inject, updated_at") \
            .order("category") \
            .order("name") \
            .execute()

        if not result.data:
            return []

        lines = []
        for row in result.data:
            inject = "★" if row["auto_inject"] else " "
            ts = row.get("updated_at", "")[:10]
            lines.append(f"{inject} [{row['category']}] {row['name']} (updated {ts})")

        return lines

    except Exception as e:
        print(f"⚠️  List notes failed: {e}", flush=True)
        return []


def get_relevant_notes(query: str) -> list[dict]:
    """
    Scan note names for relevance to the query (simple keyword matching).
    Returns list of {name, content} dicts for injection.
    """
    try:
        result = get_client().table("notes") \
            .select("name, category, content") \
            .eq("auto_inject", False) \
            .execute()

        if not result.data:
            return []

        query_lower = query.lower()
        relevant = []

        for row in result.data:
            # internal state notes and the journal never get keyword-injected
            # (the journal matches "mako" in half of all messages)
            if row["name"].startswith("_") or row["category"] == "journal":
                continue
            name_words = row["name"].replace("_", " ").lower()
            if any(word in query_lower for word in name_words.split() if len(word) > 3):
                relevant.append({
                    "name":    row["name"],
                    "content": row["content"],
                })

        return relevant

    except Exception as e:
        print(f"⚠️  Relevant notes failed: {e}", flush=True)
        return []


def get_note_index() -> str:
    """
    Compact index of topic notes (name + first-line snippet), so the model
    always knows what notes exist and can read_note the ones it needs.
    Excludes auto-injected notes (already in context), person notes (they
    have their own index), internal state, and the journal.
    """
    try:
        result = get_client().table("notes") \
            .select("name, category, content") \
            .eq("auto_inject", False) \
            .order("name") \
            .execute()

        lines = []
        for row in (result.data or []):
            if row["name"].startswith("_") or row["category"] in ("journal", "person"):
                continue
            first_line = (row["content"] or "").split("\n", 1)[0].strip()
            snippet = first_line.lstrip("#> ").strip()[:60]
            lines.append(f"- {row['name']}: {snippet}" if snippet else f"- {row['name']}")
        return "\n".join(lines)

    except Exception as e:
        print(f"⚠️  Note index failed: {e}", flush=True)
        return ""


def get_notes_by_category(category: str) -> list[dict]:
    """All notes in a category as {name, content} dicts."""
    try:
        result = get_client().table("notes") \
            .select("name, content") \
            .eq("category", category) \
            .order("name") \
            .execute()
        return result.data or []
    except Exception as e:
        print(f"⚠️  Notes by category failed: {e}", flush=True)
        return []


def append_note(name: str, line: str, category: str = "general",
                max_chars: int = 10000):
    """
    Append a line to a note, creating it if needed.
    Oldest lines are trimmed once the note exceeds max_chars.
    """
    try:
        existing = get_note(name) or ""
        content = (existing + "\n" + line).strip() if existing else line
        if len(content) > max_chars:
            # drop oldest lines until it fits
            lines = content.split("\n")
            while lines and len("\n".join(lines)) > max_chars:
                lines.pop(0)
            content = "\n".join(lines)
        write_note(name, content, category=category)
    except Exception as e:
        print(f"⚠️  Append note failed: {e}", flush=True)


def delete_note(name: str):
    """Delete a note by name."""
    try:
        get_client().table("notes").delete().eq("name", name).execute()
        print(f"🗑️  Note deleted: {name}", flush=True)
    except Exception as e:
        print(f"⚠️  Delete note failed: {e}", flush=True)
