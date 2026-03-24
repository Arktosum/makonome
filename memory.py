# memory.py — Supabase backend with semantic + recency retrieval and notes system
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastembed import TextEmbedding
from supabase import create_client

load_dotenv()

# ── Embedding model ───────────────────────────────────────────────────────────
print("📥 Loading embedding model...", flush=True)
_embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
print("✅ Embedding model ready", flush=True)

# ── Supabase client ───────────────────────────────────────────────────────────
_sb = None

def _get_client():
    global _sb
    if _sb is None:
        url = os.getenv("VECTORDB_SUPABASE_URL") or os.getenv("SUPABASE_URL")
        key = os.getenv("VECTORDB_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials not set in .env")
        _sb = create_client(url, key)
    return _sb


# ── Core memory functions ─────────────────────────────────────────────────────

def save_memory(role: str, content: str):
    """Embed and save a conversation turn."""
    try:
        embedding = list(_embedder.embed([content]))[0].tolist()
        _get_client().table("memories").insert({
            "role":      role,
            "content":   content,
            "embedding": embedding,
            "timestamp": datetime.now().isoformat(),
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
        sb = _get_client()
        seen_ids = set()
        results = []

        # ── Semantic retrieval ──────────────────────────────
        query_embedding = list(_embedder.embed([query]))[0].tolist()
        semantic = sb.rpc("match_memories", {
            "query_embedding": query_embedding,
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


def clear_memories():
    """Wipe all episodic memories."""
    try:
        _get_client().table("memories") \
            .delete() \
            .neq("id", "00000000-0000-0000-0000-000000000000") \
            .execute()
        print("✅ All memories cleared.")
    except Exception as e:
        print(f"⚠️  Clear failed: {e}", flush=True)


# ── Notes system ──────────────────────────────────────────────────────────────

def get_auto_inject_notes() -> str:
    """
    Retrieve all notes marked auto_inject=true.
    These are always included in every system prompt.
    Returns formatted string ready to inject.
    """
    try:
        result = _get_client().table("notes") \
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
        result = _get_client().table("notes") \
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


def write_note(name: str, content: str, category: str = "general", auto_inject: bool = False):
    """
    Create or fully overwrite a note.
    Used by Mako when she decides to create/update a note.
    """
    try:
        sb = _get_client()

        existing = sb.table("notes") \
            .select("id") \
            .eq("name", name) \
            .limit(1) \
            .execute()

        if existing.data:
            sb.table("notes").update({
                "content":    content,
                "updated_at": datetime.now().isoformat(),
            }).eq("name", name).execute()
            print(f"📝 Note updated: {name}", flush=True)
        else:
            sb.table("notes").insert({
                "name":        name,
                "content":     content,
                "category":    category,
                "auto_inject": auto_inject,
                "updated_at":  datetime.now().isoformat(),
            }).execute()
            print(f"📝 Note created: {name}", flush=True)

    except Exception as e:
        print(f"⚠️  Write note failed: {e}", flush=True)


def list_notes() -> list[str]:
    """Return list of all note names Mako can access."""
    try:
        result = _get_client().table("notes") \
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
    Scan note names and categories for relevance to the query.
    Simple keyword matching — returns list of {name, content} dicts.
    Called by brain.py to optionally inject topic notes.
    """
    try:
        result = _get_client().table("notes") \
            .select("name, category, content") \
            .eq("auto_inject", False) \
            .execute()

        if not result.data:
            return []

        query_lower = query.lower()
        relevant = []

        for row in result.data:
            name_words = row["name"].replace("_", " ").lower()
            # check if any word in the note name appears in the query
            if any(word in query_lower for word in name_words.split() if len(word) > 3):
                relevant.append({
                    "name":    row["name"],
                    "content": row["content"],
                })

        return relevant

    except Exception as e:
        print(f"⚠️  Relevant notes failed: {e}", flush=True)
        return []