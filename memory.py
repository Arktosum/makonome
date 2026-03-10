# memory.py — Supabase pgvector backend
import os
from datetime import datetime
from dotenv import load_dotenv
from fastembed import TextEmbedding
from supabase import create_client

load_dotenv()

# ── Embedding model ───────────────────────────────────────────────────────────
# fastembed — lightweight ONNX-based, no PyTorch needed
# bge-small-en-v1.5 = 384 dimensions, matches our Supabase vector column
print("📥 Loading embedding model...", flush=True)
_embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
print("✅ Embedding model ready", flush=True)

# ── Supabase client ───────────────────────────────────────────────────────────
_sb = None


def _get_client():
    global _sb
    if _sb is None:
        url = os.getenv("VECTORDB_SUPABASE_URL")
        key = os.getenv("VECTORDB_SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError(
                "VECTORDB_SUPABASE_URL and VECTORDB_SUPABASE_ANON_KEY must be set in .env")
        _sb = create_client(url, key)
    return _sb

# ── Core functions ────────────────────────────────────────────────────────────


def save_memory(role: str, content: str):
    """
    Embed and save a single conversation turn to Supabase.
    role: 'user' or 'assistant'
    content: what was said
    """
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


def retrieve_memories(query: str, n_results: int = 10) -> list[str]:
    """
    Semantic search — find the most relevant past memories for this query.
    Returns a list of formatted strings ready to inject into the prompt.
    """
    try:
        query_embedding = list(_embedder.embed([query]))[0].tolist()

        # pgvector cosine similarity search via Supabase RPC
        result = _get_client().rpc("match_memories", {
            "query_embedding": query_embedding,
            "match_count":     n_results,
        }).execute()

        if not result.data:
            return []

        formatted = []
        for row in result.data:
            ts = row.get("timestamp", "")[:10]
            formatted.append(f"[{row['role']} - {ts}]: {row['content']}")

        return formatted

    except Exception as e:
        print(f"⚠️  Memory retrieve failed: {e}", flush=True)
        return []


def clear_memories():
    """Wipe all memories. Used by utils/clear_memory.py"""
    try:
        _get_client().table("memories").delete().neq(
            "id", "00000000-0000-0000-0000-000000000000").execute()
        print("✅ All memories cleared.")
    except Exception as e:
        print(f"⚠️  Clear failed: {e}", flush=True)


# ── Facts (Layer 1 — core identity) ──────────────────────────────────────────

def save_fact(category: str, fact: str, confidence: int = 3, expires_days: int = None):
    """
    Save or update a core fact about the user.
    expires_days=None means permanent (Layer 1 identity).
    expires_days=7 means current context (Layer 2).
    """
    from datetime import timedelta
    try:
        sb = _get_client()

        expires_at = None
        if expires_days is not None:
            expires_at = (datetime.now() +
                          timedelta(days=expires_days)).isoformat()

        # check if a similar fact exists in this category
        existing = sb.table("facts") \
            .select("id, fact") \
            .eq("category", category) \
            .execute()

        # simple dedup — if first 40 chars match, treat as same fact and update
        for row in (existing.data or []):
            if row["fact"][:40].lower() == fact[:40].lower():
                sb.table("facts").update({
                    "fact":       fact,
                    "confidence": confidence,
                    "expires_at": expires_at,
                    "updated_at": datetime.now().isoformat(),
                }).eq("id", row["id"]).execute()
                layer = "context" if expires_days else "fact"
                print(
                    f"📝 {layer.title()} updated [{category}]: {fact[:60]}", flush=True)
                return

        # insert new fact
        sb.table("facts").insert({
            "category":   category,
            "fact":       fact,
            "confidence": confidence,
            "expires_at": expires_at,
            "updated_at": datetime.now().isoformat(),
        }).execute()
        layer = "Context" if expires_days else "Fact"
        print(f"📝 {layer} saved [{category}]: {fact[:60]}", flush=True)

    except Exception as e:
        print(f"⚠️  Fact save failed: {e}", flush=True)


def get_all_facts() -> str:
    """
    Retrieve all non-expired facts grouped by layer and category.
    Layer 1 = permanent facts (expires_at is null)
    Layer 2 = current context (expires_at is set, not yet expired)
    Returns a formatted string ready to inject into the system prompt.
    """
    try:
        now = datetime.now().isoformat()
        result = _get_client().table("facts") \
            .select("category, fact, confidence, expires_at") \
            .order("category") \
            .order("confidence", desc=True) \
            .execute()

        if not result.data:
            return ""

        permanent = {}   # Layer 1 — no expiry
        context = {}   # Layer 2 — has expiry, not yet expired

        for row in result.data:
            # skip expired rows
            if row["expires_at"] and row["expires_at"] < now:
                continue

            cat = row["category"].upper()
            if row["expires_at"] is None:
                permanent.setdefault(cat, []).append(row["fact"])
            else:
                context.setdefault(cat, []).append(row["fact"])

        lines = []

        if permanent:
            lines.append("CORE IDENTITY:")
            for cat, facts in permanent.items():
                for f in facts:
                    lines.append(f"  [{cat}] {f}")

        if context:
            lines.append("CURRENT CONTEXT (recent, time-sensitive):")
            for cat, facts in context.items():
                for f in facts:
                    lines.append(f"  [{cat}] {f}")

        return "\n".join(lines)

    except Exception as e:
        print(f"⚠️  Facts retrieve failed: {e}", flush=True)
        return ""
