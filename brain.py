# brain.py
import os
import json
import asyncio
from datetime import datetime
from collections import deque
from groq import Groq
from dotenv import load_dotenv
from config import GROQ_MODEL, SYSTEM_PROMPT
from memory import retrieve_memories, save_memory

load_dotenv()
_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Conversation buffer ───────────────────────────────────────────────────────
# Keeps the last N turns in memory so Mako has short-term context.
# This is separate from ChromaDB — this is live conversation context,
# not long-term semantic memory.
BUFFER_SIZE = 6  # number of turns to keep (each turn = 1 user + 1 assistant)
_conversation_buffer = deque(maxlen=BUFFER_SIZE * 2)  # *2 because each turn is 2 messages

def _add_to_buffer(role: str, content: str):
    _conversation_buffer.append({"role": role, "content": content})

def _get_buffer_context() -> str:
    """Format buffer as a readable context block for the system prompt."""
    if not _conversation_buffer:
        return ""
    lines = []
    for msg in _conversation_buffer:
        label = "Siddhu" if msg["role"] == "user" else "Mako"
        lines.append(f"{label}: {msg['content']}")
    return "\n".join(lines)

# ── Tools prompt ──────────────────────────────────────────────────────────────
TOOLS_PROMPT = """

CRITICAL: You have real tools available. When you write ACTION: {...} the system 
will ACTUALLY execute that tool and return real results. Do NOT make up results.
Do NOT write [Search results] or [Read content] — wait for the REAL tool result.
NEVER fabricate news, weather, or any external data.

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
- get_account_balances: Get all account balances. Args: {}
- get_spending_summary: Income vs expenses summary. Args: {"days": 30}
- get_spending_by_category: Spending breakdown by category. Args: {"days": 30}
- get_recent_transactions: Recent transaction list. Args: {"limit": 10}
- get_unsettled_debts: Who owes who. Args: {}
- get_top_merchants: Top spending merchants. Args: {"days": 30}

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

# ── Tool dispatcher ───────────────────────────────────────────────────────────
def _run_tool(tool_name: str, args: dict) -> str:
    if tool_name == "web_search":
        from tools.search import web_search
        return web_search(args.get("query", ""))
    elif tool_name == "fetch_page":
        from tools.search import fetch_page
        return fetch_page(args.get("url", ""))
    elif tool_name == "get_weather":
        from tools.weather import get_weather
        return get_weather(args.get("city", ""))
    elif tool_name == "open_app":
        from tools.system import open_app
        return open_app(args.get("app_name", ""))
    elif tool_name == "read_file":
        from tools.system import read_file
        return read_file(args.get("path", ""))
    elif tool_name == "write_file":
        from tools.system import write_file
        return write_file(args.get("path", ""), args.get("content", ""))
    elif tool_name == "get_account_balances":
        from tools.finance import get_account_balances
        return get_account_balances()
    elif tool_name == "get_spending_summary":
        from tools.finance import get_spending_summary
        return get_spending_summary(int(args.get("days", 30)))
    elif tool_name == "get_spending_by_category":
        from tools.finance import get_spending_by_category
        return get_spending_by_category(int(args.get("days", 30)))
    elif tool_name == "get_recent_transactions":
        from tools.finance import get_recent_transactions
        return get_recent_transactions(int(args.get("limit", 10)))
    elif tool_name == "get_unsettled_debts":
        from tools.finance import get_unsettled_debts
        return get_unsettled_debts()
    elif tool_name == "get_top_merchants":
        from tools.finance import get_top_merchants
        return get_top_merchants(int(args.get("days", 30)))
    else:
        return f"Unknown tool: {tool_name}"

# ── Tool call parser ──────────────────────────────────────────────────────────
def _is_tool_call(text: str) -> dict | None:
    # look for ACTION: {...} pattern
    try:
        if 'ACTION:' in text:
            action_part = text.split('ACTION:')[-1].strip()
            start = action_part.index('{')
            end   = action_part.rindex('}') + 1
            data  = json.loads(action_part[start:end])
            if "tool" in data:
                return data
    except (ValueError, json.JSONDecodeError):
        pass

    # fallback — plain JSON response
    try:
        text = text.strip()
        start = text.index('{')
        end   = text.rindex('}') + 1
        data  = json.loads(text[start:end])
        if "tool" in data:
            return data
    except (ValueError, json.JSONDecodeError):
        pass

    return None

def _clean_response(text: str) -> str:
    """Strip THOUGHT/ACTION/FINAL ANSWER prefixes from final response."""
    lines = text.split('\n')
    clean = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('THOUGHT:'):
            continue
        if stripped.startswith('ACTION:'):
            continue
        if stripped.startswith('FINAL ANSWER:'):
            clean.append(line.split('FINAL ANSWER:', 1)[-1].strip())
            continue
        clean.append(line)
    return '\n'.join(clean).strip()

# ── Dashboard emitter ─────────────────────────────────────────────────────────
def _emit(event: dict):
    """Send event to dashboard via the thread-safe queue."""
    try:
        from dashboard.server import event_queue
        event.setdefault("time", datetime.now().strftime("%H:%M:%S"))
        event_queue.put(event)
    except Exception as e:
        print(f"⚠️ Emit error: {e}", flush=True)

# ── LLM call ─────────────────────────────────────────────────────────────────
def _llm(messages: list) -> str:
    """Call Groq and return the response text."""
    response = _groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )

    # log token usage + remaining limits from headers
    usage = response.usage
    headers = response._headers if hasattr(response, '_headers') else {}
    remaining_req = headers.get('x-ratelimit-remaining-requests', '?')
    remaining_tok = headers.get('x-ratelimit-remaining-tokens', '?')

    print(f"   tokens — prompt: {usage.prompt_tokens} | completion: {usage.completion_tokens} | total: {usage.total_tokens}", flush=True)
    print(f"   limits — requests left today: {remaining_req} | tokens left this min: {remaining_tok}", flush=True)

    return response.choices[0].message.content

# ── Timing helper ─────────────────────────────────────────────────────────────
def _t(label: str, start: float):
    import time
    elapsed = time.time() - start
    print(f"⏱  {label}: {elapsed:.2f}s", flush=True)
    return time.time()

# ── Main think function ───────────────────────────────────────────────────────
def think(user_message: str) -> str:
    """
    Main function. Takes user message, retrieves memories + recent conversation,
    calls LLM with ReAct agentic loop, saves to memory, returns response.
    """
    import time
    t0 = time.time()
    print(f"\n{'─'*50}", flush=True)
    print(f"🧠 think() called: {user_message[:60]}", flush=True)

    # 1. retrieve long-term semantic memories
    t = time.time()
    memories = retrieve_memories(user_message)
    t = _t("1. memory retrieve", t)

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

    # inject long-term memories
    if memories:
        memory_block = "\n".join(memories)
        system += f"\n\n--- RELEVANT MEMORIES ---\n{memory_block}\n--- END MEMORIES ---"

    # inject short-term conversation buffer
    buffer_context = _get_buffer_context()
    if buffer_context:
        system += f"\n\n--- RECENT CONVERSATION ---\n{buffer_context}\n--- END RECENT CONVERSATION ---"

    print(f"   system prompt: {len(system)} chars", flush=True)

    # 3. emit user message to dashboard
    _emit({
        "type": "message",
        "data": {"role": "user", "content": user_message}
    })

    # 4. build message list
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_message}
    ]

    # 5. ReAct agentic loop
    MAX_TOOL_CALLS = 8
    tool_calls_made = 0
    assistant_message = ""

    while tool_calls_made < MAX_TOOL_CALLS:
        t = time.time()
        assistant_message = _llm(messages)
        t = _t(f"2. LLM call #{tool_calls_made + 1}", t)

        tool_call = _is_tool_call(assistant_message)

        if not tool_call:
            print(f"   → final answer ({len(assistant_message)} chars)", flush=True)
            break

        # extract and emit THOUGHT if present
        if 'THOUGHT:' in assistant_message:
            thought = assistant_message.split('THOUGHT:')[1].split('ACTION:')[0].strip()
            print(f"\n💭 Mako thinks: {thought}", flush=True)
            _emit({
                "type": "thought",
                "data": {"content": thought}
            })

        tool_name = tool_call["tool"]
        args      = tool_call.get("args", {})

        print(f"\n🔧 Tool: {tool_name} | args: {args}", flush=True)

        _emit({
            "type": "tool_call",
            "data": {"tool": tool_name, "args": args}
        })

        t = time.time()
        tool_result = _run_tool(tool_name, args)
        t = _t(f"3. tool: {tool_name}", t)

        _emit({
            "type": "tool_result",
            "data": {"tool": tool_name, "result": tool_result[:500]}
        })

        messages.append({"role": "assistant", "content": assistant_message})
        messages.append({
            "role": "user",
            "content": f"Tool result for {tool_name}:\n{tool_result}\n\nContinue your reasoning. Use another tool if needed, or give your final answer if satisfied."
        })

        tool_calls_made += 1

    # 6. clean up the response
    assistant_message = _clean_response(assistant_message)

    # 7. emit final response
    _emit({
        "type": "message",
        "data": {"role": "assistant", "content": assistant_message}
    })

    # 8. save to long-term memory AND short-term buffer
    t = time.time()
    save_memory("user", user_message)
    save_memory("assistant", assistant_message)
    _t("4. memory save", t)

    _add_to_buffer("user", user_message)
    _add_to_buffer("assistant", assistant_message)

    _t("TOTAL", t0)
    print(f"{'─'*50}\n", flush=True)

    return assistant_message