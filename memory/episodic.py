# memory/episodic.py — episodic memories with semantic + recency retrieval
from datetime import datetime
from zoneinfo import ZoneInfo
from config import TIMEZONE
from memory.db import get_client, embed


def save_memory(role: str, content: str):
    """Embed and save a memory."""
    try:
        get_client().table("memories").insert({
            "role":      role,
            "content":   content,
            "embedding": embed(content),
            "timestamp": datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
        }).execute()
    except Exception as e:
        print(f"⚠️  Memory save failed: {e}", flush=True)


def retrieve_memories(query: str, n_semantic: int = 5, n_recent: int = 3) -> list[str]:
    """
    Retrieve memories using a split strategy:
    - Top N semantically similar to the query
    - Top M most recent regardless of similarity
    Merged and deduplicated.
    """
    try:
        sb = get_client()
        seen_ids = set()
        results = []

        # ── Semantic retrieval ──────────────────────────────
        semantic = sb.rpc("match_memories", {
            "query_embedding": embed(query),
            "match_count":     n_semantic,
        }).execute()

        for row in (semantic.data or []):
            seen_ids.add(row.get("id"))
            ts = (row.get("ts") or row.get("timestamp") or "")[:10]
            results.append(f"[{row['role']} - {ts}]: {row['content']}")

        # ── Recency retrieval ───────────────────────────────
        recent = sb.table("memories") \
            .select("id, role, content, timestamp") \
            .order("timestamp", desc=True) \
            .limit(n_recent * 2) \
            .execute()

        added = 0
        for row in (recent.data or []):
            if added >= n_recent:
                break
            if row["id"] in seen_ids:
                continue
            seen_ids.add(row["id"])
            ts = row.get("timestamp", "")[:10]
            results.append(f"[{row['role']} - {ts} ★recent]: {row['content']}")
            added += 1

        return results

    except Exception as e:
        print(f"⚠️  Memory retrieve failed: {e}", flush=True)
        return []


def get_last_memory_timestamp() -> str | None:
    """ISO timestamp of the most recent memory, or None."""
    try:
        result = get_client().table("memories") \
            .select("timestamp") \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()
        if result.data:
            return result.data[0]["timestamp"]
        return None
    except Exception as e:
        print(f"⚠️  Could not get last memory timestamp: {e}", flush=True)
        return None


def get_recent_memory_rows(limit: int = 6) -> list[dict]:
    """Most recent memory rows, oldest first."""
    try:
        result = get_client().table("memories") \
            .select("role, content, timestamp") \
            .order("timestamp", desc=True) \
            .limit(limit) \
            .execute()
        return list(reversed(result.data or []))
    except Exception as e:
        print(f"⚠️  Could not get recent memories: {e}", flush=True)
        return []


def clear_memories():
    """Wipe all episodic memories."""
    try:
        get_client().table("memories") \
            .delete() \
            .neq("id", "00000000-0000-0000-0000-000000000000") \
            .execute()
        print("✅ All memories cleared.")
    except Exception as e:
        print(f"⚠️  Clear failed: {e}", flush=True)
