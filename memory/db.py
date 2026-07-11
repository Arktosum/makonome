# memory/db.py — shared Supabase client + lazy embedding model
import os
from dotenv import load_dotenv
from config import EMBEDDING_MODEL

load_dotenv()

_sb = None
_embedder = None


def get_client():
    global _sb
    if _sb is None:
        url = os.getenv("VECTORDB_SUPABASE_URL") or os.getenv("SUPABASE_URL")
        key = os.getenv("VECTORDB_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials not set in .env")
        from supabase import create_client
        _sb = create_client(url, key)
    return _sb


def embed(text: str) -> list[float]:
    global _embedder
    if _embedder is None:
        print("📥 Loading embedding model...", flush=True)
        from fastembed import TextEmbedding
        _embedder = TextEmbedding(model_name=EMBEDDING_MODEL)
        print("✅ Embedding model ready", flush=True)
    return list(_embedder.embed([text]))[0].tolist()
