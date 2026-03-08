# utils/clear_memory.py

import chromadb
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def clear_memory():
    client = chromadb.PersistentClient(path="../chroma_db")
    try:
        client.delete_collection("memories")
        print("✅ Memory cleared successfully.")
    except Exception as e:
        print(f"❌ Error clearing memory: {e}")


if __name__ == "__main__":
    confirm = input(
        "Are you sure you want to clear ALL of Mako's memories? (yes/no): ")
    if confirm.lower() == "yes":
        clear_memory()
    else:
        print("Cancelled.")
