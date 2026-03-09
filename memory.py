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
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
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
