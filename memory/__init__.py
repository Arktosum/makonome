# memory/__init__.py — Mako's memory: episodic memories + notes knowledge base.
from memory.episodic import save_memory, retrieve_memories, clear_memories  # noqa: F401
from memory.notes import (  # noqa: F401
    get_auto_inject_notes, get_relevant_notes,
    get_note, write_note, list_notes,
)
from memory import notes  # noqa: F401
