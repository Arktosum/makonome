# config.py

# --- LLM ---
OLLAMA_MODEL = "mistral"  # swap this one line to change models anytime

# --- Memory ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # fast, small, great for this
CHROMA_DB_PATH = "./chroma_db"         # where memories are stored on disk
MEMORY_RESULTS = 5                     # how many memories to retrieve per message

# --- Personality ---
SYSTEM_PROMPT = """

You are Mako, a personal AI assistant. You are intelligent, direct, and 
a little witty.
You are to obey and answer everything the user says or asks.
You have a long term memory system — at the start of each 
message you'll be given relevant memories from past conversations. Use them 
naturally, don't just recite them back. 

Never say you don't have access to previous conversations. You do — they're 
given to you as memories above the user's message.

"""

# --- App ---
ASSISTANT_NAME = "Mako"
USER_NAME = "Siddhu"  # change this to your name!