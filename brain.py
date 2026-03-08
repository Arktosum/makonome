# brain.py
import ollama
import json
import asyncio
from datetime import datetime
from config import OLLAMA_MODEL, SYSTEM_PROMPT
from memory import retrieve_memories, save_memory
import re

def _clean_response(text: str) -> str:
    """Remove internal reasoning tokens from final response."""
    # remove THOUGHT: ... blocks
    text = re.sub(r'THOUGHT:.*?(?=ACTION:|FINAL ANSWER:|$)', '', text, flags=re.DOTALL)
    # remove ACTION: ... blocks  
    text = re.sub(r'ACTION:.*?(?=THOUGHT:|FINAL ANSWER:|$)', '', text, flags=re.DOTALL)
    # remove FINAL ANSWER: prefix
    text = re.sub(r'FINAL ANSWER:\s*', '', text)
    # remove leftover artifacts
    text = re.sub(r'\[.*?\]', '', text)
    return text.strip()

TOOLS_PROMPT = """
You have access to tools and you should use them thoroughly before answering.

THINKING PROCESS — always follow this pattern:
THOUGHT: [reason about what you need to do]
ACTION: {"tool": "tool_name", "args": {"arg1": "value1"}}

When you have gathered enough information, give your final answer as normal text
with no THOUGHT or ACTION prefix.

AVAILABLE TOOLS:
- web_search: Search the internet. Args: {"query": "..."}
- fetch_page: Read actual content of a URL. Args: {"url": "https://..."}
- get_weather: Get weather for a city. Args: {"city": "..."}
- open_app: Open an app or website. Args: {"app_name": "..."}
- read_file: Read a file's contents. Args: {"path": "..."}
- write_file: Write content to a file. Args: {"path": "...", "content": "..."}

RULES:
- NEVER answer questions about current events, news, or weather from memory
- ALWAYS search first, fetch the most relevant page, then summarize
- Keep using tools until you genuinely have enough to give a great answer
- Only give your final answer when you are actually satisfied with what you found
- If a page doesn't have what you need, fetch a different one

EXAMPLES:

User: "what's in the news today?"
THOUGHT: I need to search for today's news first
ACTION: {"tool": "web_search", "args": {"query": "top news today"}}
[sees results]
THOUGHT: Let me read the top result to get actual content
ACTION: {"tool": "fetch_page", "args": {"url": "https://..."}}
[reads content]
THOUGHT: I have enough to give a good summary now
[gives final answer]

User: "what's the weather in Chennai?"
THOUGHT: I should get the current weather data
ACTION: {"tool": "get_weather", "args": {"city": "Chennai"}}
[gets result]
[gives final answer]
"""


def _run_tool(tool_name: str, args: dict) -> str:
    from tools.search import web_search, fetch_page
    from tools.weather import get_weather
    from tools.system import open_app, read_file, write_file

    if tool_name == "web_search":
        return web_search(args.get("query", ""))
    elif tool_name == "fetch_page":
        return fetch_page(args.get("url", ""))
    elif tool_name == "get_weather":
        return get_weather(args.get("city", ""))
    elif tool_name == "open_app":
        return open_app(args.get("app_name", ""))
    elif tool_name == "read_file":
        return read_file(args.get("path", ""))
    elif tool_name == "write_file":
        return write_file(args.get("path", ""), args.get("content", ""))
    else:
        return f"Unknown tool: {tool_name}"


def _is_tool_call(text: str) -> dict | None:
    # look for ACTION: {...} pattern
    try:
        if 'ACTION:' in text:
            action_part = text.split('ACTION:')[-1].strip()
            start = action_part.index('{')
            end = action_part.rindex('}') + 1
            data = json.loads(action_part[start:end])
            if "tool" in data:
                return data
    except (ValueError, json.JSONDecodeError):
        pass

    # fallback — plain JSON response
    try:
        text = text.strip()
        start = text.index('{')
        end = text.rindex('}') + 1
        data = json.loads(text[start:end])
        if "tool" in data:
            return data
    except (ValueError, json.JSONDecodeError):
        pass

    return None


def _emit(event: dict):
    print(f"🔵 EMIT CALLED: {event.get('type')}", flush=True)
    try:
        from dashboard.server import event_queue
        event_queue.put(event)
    except Exception as e:
        print(f"🔴 EMIT ERROR: {e}", flush=True)


def think(user_message: str) -> str:
    """
    Main function with agentic tool loop.
    Mako can call multiple tools sequentially before giving a final answer.
    """

    # 1. retrieve relevant memories
    memories = retrieve_memories(user_message)
    if memories:
        _emit({
            "type": "memory",
            "data": {
                "query": user_message[:60],
                "results": memories
            }
        })

    # 2. build system prompt
    current_time = datetime.now().strftime("%A, %B %d %Y, %I:%M %p")
    system = f"Current date and time: {current_time}\n\n"
    system += SYSTEM_PROMPT + TOOLS_PROMPT
    if memories:
        memory_block = "\n".join(memories)
        system += f"\n\n--- RELEVANT MEMORIES ---\n{memory_block}\n--- END MEMORIES ---"

    # 3. emit user message to dashboard
    _emit({
        "type": "message",
        "data": {"role": "user", "content": user_message}
    })

    # 4. build message history — this grows as tools are called
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_message}
    ]

    # 5. agentic loop
    MAX_TOOL_CALLS = 8
    tool_calls_made = 0

    while tool_calls_made < MAX_TOOL_CALLS:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        assistant_message = response["message"]["content"]

        tool_call = _is_tool_call(assistant_message)

        if not tool_call:
            # no tool call — final answer
            break

        # extract and display thought if present
        if 'THOUGHT:' in assistant_message:
            thought = assistant_message.split(
                'THOUGHT:')[1].split('ACTION:')[0].strip()
            print(f"\n💭 Mako thinks: {thought}", flush=True)
            _emit({
                "type": "thought",
                "data": {"content": thought}
            })

        tool_name = tool_call["tool"]
        args = tool_call.get("args", {})

        print(f"\n🔧 Tool: {tool_name} | args: {args}", flush=True)

        _emit({
            "type": "tool_call",
            "data": {"tool": tool_name, "args": args}
        })

        tool_result = _run_tool(tool_name, args)

        _emit({
            "type": "tool_result",
            "data": {"tool": tool_name, "result": tool_result[:500]}
        })

        print(f"📦 Tool result received for {tool_name}.", flush=True)

        messages.append({"role": "assistant", "content": assistant_message})
        messages.append({
            "role": "user",
            "content": f"Tool result for {tool_name}:\n{tool_result}\n\nContinue your reasoning. Use another tool if needed, or give your final answer if satisfied."
        })

        tool_calls_made += 1

    # 6. emit final response + save to memory
    _emit({
        "type": "message",
        "data": {"role": "assistant", "content": assistant_message}
    })

    save_memory("user", user_message)
    save_memory("assistant", assistant_message)
    
    assistant_message = _clean_response(assistant_message)
    
    return assistant_message
