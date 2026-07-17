# memory/episodic.py — episodic memories with semantic + recency retrieval.
#
# Importance (Stanford generative-agents style): memories carry a "[!N]"
# prefix (1-10). Retrieval fetches extra candidates and re-ranks by
# similarity-order + importance, so "Gayathri got the job" outranks
# "asked about the weather" forever. Tags are stripped before display.
#
# Write-time dedup (Mem0 style): near-duplicates of recent memories are
# skipped at save — quality is decided when writing, not when reading.

import json
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from config import TIMEZONE
from memory.db import get_client, embed

_IMPORTANCE_RE = re.compile(r"^\[!(\d{1,2})\]\s*")
DEDUPE_THRESHOLD = 0.90
DEFAULT_IMPORTANCE = 5


def _parse_importance(content: str) -> tuple[int, str]:
    """-> (importance, content_without_tag)"""
    m = _IMPORTANCE_RE.match(content)
    if not m:
        return DEFAULT_IMPORTANCE, content
    return max(1, min(10, int(m.group(1)))), content[m.end():]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _as_vector(value) -> list[float] | None:
    """Supabase returns pgvector columns as JSON-ish strings."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def get_recent_with_embeddings(limit: int = 30) -> list[dict]:
    try:
        result = get_client().table("memories") \
            .select("id, role, content, timestamp, embedding") \
            .order("timestamp", desc=True) \
            .limit(limit) \
            .execute()
        rows = result.data or []
        for r in rows:
            r["embedding"] = _as_vector(r.get("embedding"))
        return rows
    except Exception as e:
        print(f"⚠️  Recent-with-embeddings failed: {e}", flush=True)
        return []


def save_memory(role: str, content: str, importance: int | None = None,
                dedupe: bool = False) -> bool:
    """
    Embed and save a memory. Returns True if saved, False if skipped/failed.
    With dedupe=True, a near-duplicate of a recent memory is not saved again.
    """
    try:
        vector = embed(content)

        if dedupe:
            for row in get_recent_with_embeddings(limit=30):
                other = row.get("embedding")
                if other and _cosine(vector, other) >= DEDUPE_THRESHOLD:
                    print(f"♻️  Skipped near-duplicate memory "
                          f"(~{row['content'][:50]!r})", flush=True)
                    return False

        if importance is not None:
            content = f"[!{max(1, min(10, int(importance)))}] {content}"

        get_client().table("memories").insert({
            "role":      role,
            "content":   content,
            "embedding": vector,
            "timestamp": datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
        }).execute()
        return True
    except Exception as e:
        print(f"⚠️  Memory save failed: {e}", flush=True)
        return False


def delete_memory(memory_id) -> bool:
    """Delete one memory by id (housekeeping only)."""
    try:
        get_client().table("memories").delete().eq("id", memory_id).execute()
        return True
    except Exception as e:
        print(f"⚠️  Memory delete failed: {e}", flush=True)
        return False


def retrieve_memories(query: str, n_semantic: int = 5, n_recent: int = 3) -> list[str]:
    """
    Retrieve memories using a split strategy:
    - 2×N semantic candidates, re-ranked by similarity-order + importance,
      top N kept
    - Top M most recent regardless of similarity
    Merged and deduplicated; importance tags stripped from the output.
    """
    try:
        sb = get_client()
        seen_ids = set()
        results = []

        # ── Semantic retrieval with importance re-rank ──────
        semantic = sb.rpc("match_memories", {
            "query_embedding": embed(query),
            "match_count":     n_semantic * 2,
        }).execute()

        candidates = []
        for idx, row in enumerate(semantic.data or []):
            importance, clean = _parse_importance(row["content"])
            # similarity order (idx) fights importance; a 10 beats ~7 ranks
            candidates.append((idx - importance * 0.7, importance, clean, row))

        candidates.sort(key=lambda c: c[0])
        for _, importance, clean, row in candidates[:n_semantic]:
            seen_ids.add(row.get("id"))
            ts = (row.get("ts") or row.get("timestamp") or "")[:10]
            results.append(f"[{row['role']} - {ts}]: {clean}")

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
            _, clean = _parse_importance(row["content"])
            results.append(f"[{row['role']} - {ts} ★recent]: {clean}")
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


def get_memories_since(iso_timestamp: str, limit: int = 200) -> list[dict]:
    """All memories after a given ISO timestamp, oldest first."""
    try:
        result = get_client().table("memories") \
            .select("role, content, timestamp") \
            .gt("timestamp", iso_timestamp) \
            .order("timestamp") \
            .limit(limit) \
            .execute()
        return result.data or []
    except Exception as e:
        print(f"⚠️  Could not get memories since {iso_timestamp[:10]}: {e}", flush=True)
        return []


def get_recent_memory_rows(limit: int = 6) -> list[dict]:
    """Most recent memory rows, oldest first."""
    try:
        result = get_client().table("memories") \
            .select("role, content, timestamp") \
            .order("timestamp", desc=True) \
            .limit(limit) \
            .execute()
        rows = list(reversed(result.data or []))
        for r in rows:
            _, r["content"] = _parse_importance(r["content"])
        return rows
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
