# tools/memory.py — lets Mako actively dig through her own past,
# beyond the handful of memories auto-injected each turn.
from tools.registry import tool
from memory.episodic import retrieve_memories, get_recent_memory_rows


@tool(
    description=(
        "Search your long-term memory for past conversations and events. "
        "Use when you need more than what's already in context — e.g. "
        "'when did we first talk about X', checking an old detail, or "
        "gathering everything you know about a topic or person."
    ),
    params={"query": {"type": "string",
                      "description": "what to search your memories for"}},
)
def search_memories(query: str) -> str:
    results = retrieve_memories(query, n_semantic=10, n_recent=0)
    if not results:
        return "No memories found for that."
    return "\n".join(results)


@tool(
    description="Get your most recent memories in chronological order.",
    params={"limit": {"type": "integer",
                      "description": "how many (default 10, max 30)"}},
    required=[],
)
def recent_memories(limit: int = 10) -> str:
    rows = get_recent_memory_rows(limit=min(int(limit or 10), 30))
    if not rows:
        return "No memories yet."
    return "\n".join(
        f"[{r.get('timestamp', '')[:10]}] ({r['role']}) {r['content']}" for r in rows
    )
