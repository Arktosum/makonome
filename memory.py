# memory.py
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime
import uuid
from config import EMBEDDING_MODEL, CHROMA_DB_PATH, MEMORY_RESULTS

# This is the embedding function — sentence-transformers under the hood
# It downloads the model once on first run, then caches it locally
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

# Connect to (or create) our local ChromaDB database
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# A "collection" is like a table in a regular database
# We store all memories in one collection called "memories"
collection = client.get_or_create_collection(
    name="memories",
    embedding_function=embedding_fn
)

def save_memory(role: str, content: str):
    """
    Save a single conversation turn to memory.
    role is either "user" or "assistant"
    content is what was said
    """
    collection.add(
        documents=[content],
        metadatas=[{
            "role": role,
            "timestamp": datetime.now().isoformat()
        }],
        ids=[str(uuid.uuid4())]  # unique ID for each memory
    )

def retrieve_memories(query: str) -> list[str]:
    """
    Given the user's current message, find the most semantically
    similar past memories and return them as a list of strings.
    """
    # Don't search if memory is empty (would throw an error)
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(MEMORY_RESULTS, collection.count())
    )

    # results["documents"] is a list of lists, we want the inner list
    memories = results["documents"][0]
    metadatas = results["metadatas"][0]

    # Format each memory nicely so the LLM understands context
    formatted = []
    for mem, meta in zip(memories, metadatas):
        formatted.append(f"[{meta['role']} - {meta['timestamp'][:10]}]: {mem}")

    return formatted