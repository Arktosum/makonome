# brain.py
import ollama
from config import OLLAMA_MODEL, SYSTEM_PROMPT, ASSISTANT_NAME, USER_NAME
from memory import retrieve_memories, save_memory

def chat(user_message: str) -> str:
    """
    Main function — takes user input, retrieves memories,
    builds prompt, gets LLM response, saves everything to memory.
    """

    # Step 1: retrieve relevant memories for this message
    memories = retrieve_memories(user_message)

    # Step 2: build the system prompt, injecting memories if we have any
    system = SYSTEM_PROMPT
    if memories:
        memory_block = "\n".join(memories)
        system += f"\n\n--- RELEVANT MEMORIES ---\n{memory_block}\n--- END MEMORIES ---"

    # Step 3: call Ollama with our system prompt + user message
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message}
        ]
    )

    assistant_message = response["message"]["content"]

    # Step 4: save both sides of the conversation to memory
    save_memory("user", user_message)
    save_memory("assistant", assistant_message)

    return assistant_message