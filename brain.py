# brain.py
import os
import json
import threading
from datetime import datetime
from collections import deque
from groq import Groq
from dotenv import load_dotenv
from config import GROQ_MODEL, SYSTEM_PROMPT, USER_NAME, ASSISTANT_NAME
from memory import retrieve_memories, save_memory, save_fact, get_all_facts

load_dotenv()
_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Session tracking ──────────────────────────────────────────────────────────
_session_start = datetime.now()


def get_session_context() -> str:
    delta = datetime.now() - _session_start
    s = int(delta.total_seconds())
    if s < 60:
        return "just came online"
    elif s < 3600:
        m = s//60
        return f"online for {m} minute{'s' if m != 1 else ''}"
    else:
        h = s//3600
        m = (s % 3600)//60
        return f"online for {h}h {m}m"


# ── Conversation buffer ───────────────────────────────────────────────────────
BUFFER_SIZE = 6
_conversation_buffer = deque(maxlen=BUFFER_SIZE * 2)


def _add_to_buffer(role: str, content: str):
    _conversation_buffer.append({"role": role, "content": content})


def _get_buffer_context() -> str:
    if not _conversation_buffer:
        return ""
    lines = []
    for msg in _conversation_buffer:
        label = USER_NAME if msg["role"] == "user" else ASSISTANT_NAME
        lines.append(f"{label}: {msg['content']}")
    return "\n".join(lines)


# ── Tools prompt ──────────────────────────────────────────────────────────────
TOOLS_PROMPT = """
You have access to tools. You MUST follow this format strictly.

STRICT FORMAT RULES:
1. Each response must be EITHER a tool call OR a final answer. NEVER both.
2. If you need to use a tool, respond with ONLY this — nothing else:
   THOUGHT: [your reasoning]
   ACTION: {"tool": "tool_name", "args": {"key": "value"}}
3. After receiving tool results, either call another tool OR give your final answer.
4. Final answer = plain conversational text with NO tool syntax, no THOUGHT, no ACTION.
5. NEVER write tool JSON in your final answer. NEVER show raw tool calls to the user.
6. NEVER fabricate tool results. Wait for the actual result before continuing.

AVAILABLE TOOLS:
- web_search: Search the internet. Args: {"query": "..."}
- fetch_page: Read a URL's full content. Args: {"url": "https://..."}
- get_weather: Get weather for a city. Args: {"city": "..."}
- open_app: Open an app or website. Args: {"app_name": "..."}
- read_file: Read a file. Args: {"path": "..."}
- write_file: Write a file. Args: {"path": "...", "content": "..."}
- get_account_balances: Get account balances. Args: {}
- get_spending_summary: Income vs expenses. Args: {"days": 30}
- get_spending_by_category: Spending by category. Args: {"days": 30}
- get_recent_transactions: Recent transactions. Args: {"limit": 10}
- get_unsettled_debts: Lent/borrowed amounts. Args: {}
- get_top_merchants: Top merchants by spend. Args: {"days": 30}

EXAMPLE — correct tool use:
User: "what's in the news today?"
You: THOUGHT: I need to search for today's news.
     ACTION: {"tool": "web_search", "args": {"query": "top news March 2026"}}
[system returns results]
You: THOUGHT: Let me read the top result for full content.
     ACTION: {"tool": "fetch_page", "args": {"url": "https://..."}}
[system returns page]
You: Here's what's happening today: [your summary in natural language]

WRONG — never do this:
You: Let me search for that. {"tool": "web_search", ...} I found some results...
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


def _clean_response(text: str) -> str:
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
        print(f"⚠️  Emit error: {e}", flush=True)

# ── LLM call ─────────────────────────────────────────────────────────────────


def _llm(messages: list) -> str:
    response = _groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )
    usage = response.usage
    print(
        f"   tokens — prompt: {usage.prompt_tokens} | completion: {usage.completion_tokens} | total: {usage.total_tokens}", flush=True)
    return response.choices[0].message.content

# ── Timing helper ─────────────────────────────────────────────────────────────


def _t(label: str, start: float):
    import time
    elapsed = time.time() - start
    print(f"⏱  {label}: {elapsed:.2f}s", flush=True)
    return time.time()


# ── Proactive memory filter ───────────────────────────────────────────────────
_MEMORY_FILTER_PROMPT = f"""You are a memory curator for an AI assistant called Mako.

Your job: analyze a conversation exchange between {USER_NAME} and Mako and extract:
1. Memories worth saving (episodic — what happened, what was discussed)
2. Core facts about {USER_NAME} (identity — who they are, permanent or semi-permanent)

FACTS go in the facts list. Use these categories:
- identity: name, age, location, occupation
- preferences: likes, dislikes, habits, communication style
- projects: things they are working on
- relationships: people in their life
- health: physical or mental health context
- goals: aspirations, plans

MEMORIES go in the memories list:
- Important events (upcoming plans, things that happened, milestones)
- Opinions or feelings {USER_NAME} expressed
- Things {USER_NAME} explicitly asked Mako to remember

DO NOT SAVE OR EXTRACT if it's:
- Small talk ("hey", "thanks", "ok", "cool")
- Ephemeral info (weather, news, current time)
- Anything with no lasting value

Respond in JSON only, no other text:
{{
  "save": true or false,
  "memories": [
    {{"role": "user", "content": "concise episodic memory worth saving"}}
  ],
  "facts": [
    {{
      "category": "identity|preferences|projects|relationships|health|goals",
      "fact": "concise fact about {USER_NAME}",
      "confidence": 1-5,
      "temporary": true or false
    }}
  ]
}}

temporary=false means permanent identity (Layer 1): name, location, job, long-term preferences.
temporary=true means current context (Layer 2): upcoming events, short-term plans, recent happenings.
Confidence guide: 5=explicitly stated, 3=clearly implied, 1=weak inference.
If save is false, both lists can be empty.
Keep everything concise — signal only, no noise.
"""


def _filter_and_extract(user_message: str, assistant_message: str) -> tuple[list[dict], list[dict]]:
    """
    Ask Groq to extract memories AND facts from this exchange.
    Returns (memories, facts) — both can be empty lists.
    Falls back to saving raw messages if extraction fails.
    """
    try:
        exchange = f"{USER_NAME}: {user_message}\nMako: {assistant_message}"

        response = _groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _MEMORY_FILTER_PROMPT},
                {"role": "user",   "content": exchange}
            ],
            max_tokens=400,
            temperature=0.2,
        )

        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)

        if not data.get("save", False):
            print(f"🧹 Memory filter: nothing worth saving", flush=True)
            return [], []

        memories = data.get("memories", [])
        facts = data.get("facts", [])

        if memories:
            print(f"🧠 Memories: saving {len(memories)} item(s)", flush=True)
            for m in memories:
                print(f"   [{m['role']}] {m['content'][:80]}", flush=True)

        if facts:
            print(f"💡 Facts: extracted {len(facts)} item(s)", flush=True)
            for f in facts:
                print(
                    f"   [{f['category']}] {f['fact'][:80]} (confidence: {f['confidence']})", flush=True)

        return memories, facts

    except Exception as e:
        print(f"⚠️  Memory filter failed ({e}), saving raw", flush=True)
        return [
            {"role": "user",      "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ], []

# ── Main think function ───────────────────────────────────────────────────────


def think(user_message: str) -> str:
    """
    Main function. Takes user message, retrieves memories + recent conversation,
    calls LLM with ReAct agentic loop, saves filtered memories, returns response.
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
        _emit({"type": "memory", "data": {
              "query": user_message[:60], "results": memories}})

    # 2. build system prompt
    current_time = datetime.now().strftime("%A, %B %d %Y, %I:%M %p")
    session_ctx = get_session_context()
    system = f"Current date and time: {current_time}\nSession status: {session_ctx}\n\n"
    system += SYSTEM_PROMPT + TOOLS_PROMPT

    # inject Layer 1 — core identity facts (always present)
    facts_block = get_all_facts()
    if facts_block:
        system += f"\n\n--- WHAT I KNOW ABOUT {USER_NAME.upper()} ---\n{facts_block}\n--- END FACTS ---"

    # inject Layer 3 — relevant episodic memories (semantic search)
    if memories:
        memory_block = "\n".join(memories)
        system += f"\n\n--- RELEVANT MEMORIES ---\n{memory_block}\n--- END MEMORIES ---"

    buffer_context = _get_buffer_context()
    if buffer_context:
        system += f"\n\n--- RECENT CONVERSATION ---\n{buffer_context}\n--- END RECENT CONVERSATION ---"

    print(f"   system prompt: {len(system)} chars", flush=True)

    # 3. emit prompt debug breakdown for inspector
    def _approx_tokens(text: str) -> int:
        return max(1, int(len(text.split()) * 1.3))

    _emit({
        "type": "prompt_debug",
        "data": {
            "user_message": user_message,
            "sections": [
                {
                    "label": "SYSTEM BASE",
                    "color": "blue",
                    "text": f"Current date and time: {current_time}\nSession status: {session_ctx}\n\n" + SYSTEM_PROMPT
                },
                {
                    "label": "TOOLS",
                    "color": "purple",
                    "text": TOOLS_PROMPT
                },
                {
                    "label": "CORE IDENTITY & CONTEXT",
                    "color": "green",
                    "text": facts_block if facts_block else "(no facts yet)"
                },
                {
                    "label": "RELEVANT MEMORIES",
                    "color": "amber",
                    "text": "\n".join(memories) if memories else "(no memories retrieved)"
                },
                {
                    "label": "CONVERSATION BUFFER",
                    "color": "cyan",
                    "text": buffer_context if buffer_context else "(empty — first message)"
                },
                {
                    "label": "USER MESSAGE",
                    "color": "red",
                    "text": user_message
                },
            ]
        }
    })

    # emit user message to dashboard
    _emit({"type": "message", "data": {"role": "user", "content": user_message}})

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
            print(
                f"   → final answer ({len(assistant_message)} chars)", flush=True)
            break

        if 'THOUGHT:' in assistant_message:
            thought = assistant_message.split(
                'THOUGHT:')[1].split('ACTION:')[0].strip()
            print(f"\n💭 Mako thinks: {thought}", flush=True)
            _emit({"type": "thought", "data": {"content": thought}})

        tool_name = tool_call["tool"]
        args = tool_call.get("args", {})

        print(f"\n🔧 Tool: {tool_name} | args: {args}", flush=True)
        _emit({"type": "tool_call", "data": {"tool": tool_name, "args": args}})

        t = time.time()
        tool_result = _run_tool(tool_name, args)
        t = _t(f"3. tool: {tool_name}", t)

        _emit({"type": "tool_result", "data": {
              "tool": tool_name, "result": tool_result[:500]}})

        messages.append({"role": "assistant", "content": assistant_message})
        messages.append({
            "role": "user",
            "content": f"Tool result for {tool_name}:\n{tool_result}\n\nContinue your reasoning. Use another tool if needed, or give your final answer if satisfied."
        })
        tool_calls_made += 1

    # 6. clean response
    assistant_message = _clean_response(assistant_message)

    # 7. emit to dashboard
    _emit({"type": "message", "data": {
          "role": "assistant", "content": assistant_message}})

    # 8. update short-term buffer immediately
    _add_to_buffer("user", user_message)
    _add_to_buffer("assistant", assistant_message)

    # 9. filter and save to long-term memory in background
    #    runs after response returned so user doesn't wait for it
    def _save_filtered():
        t = time.time()
        memories_to_save, facts_to_save = _filter_and_extract(
            user_message, assistant_message)
        for item in memories_to_save:
            save_memory(item["role"], item["content"])
        for item in facts_to_save:
            expires = 7 if item.get("temporary", False) else None
            save_fact(item["category"], item["fact"], item.get(
                "confidence", 3), expires_days=expires)
        _t("4. memory+fact filter+save", t)

    threading.Thread(target=_save_filtered, daemon=True).start()

    _t("TOTAL (excl. memory save)", t0)
    print(f"{'─'*50}\n", flush=True)

    return assistant_message
