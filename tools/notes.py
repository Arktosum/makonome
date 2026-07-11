# tools/notes.py — Mako's own knowledge base, exposed as tools
from tools.registry import tool
from memory import notes


@tool(
    description="Read one of your notes by name.",
    params={"name": {"type": "string", "description": "note name, e.g. about_siddhu"}},
)
def read_note(name: str) -> str:
    content = notes.get_note(name)
    return content if content else "Note not found."


@tool(
    description="Create or update one of your notes (full rewrite of its content).",
    params={
        "name": {"type": "string", "description": "note name (snake_case)"},
        "content": {"type": "string", "description": "the complete new content of the note"},
        "category": {"type": "string", "description": "identity | context | person | project | general"},
    },
    required=["name", "content"],
)
def write_note(name: str, content: str, category: str = "general") -> str:
    notes.write_note(name, content, category=category)
    return "Note saved."


@tool(description="List all of your notes with categories and last-updated dates.")
def list_notes() -> str:
    entries = notes.list_notes()
    return "\n".join(entries) if entries else "No notes yet."
