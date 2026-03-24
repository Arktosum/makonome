# brain.py
import os
import json
import threading
from datetime import datetime
from collections import deque
from groq import Groq
from dotenv import load_dotenv
from config import GROQ_MODEL, SYSTEM_PROMPT, USER_NAME, ASSISTANT_NAME
from memory import (
    retrieve_memories, save_memory,
    get_auto_inject_notes, get_relevant_notes,
    get_note, write_note, list_notes
)

load_dotenv()
_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Session tracking ──────────────────────────────────────────────────────────
_session_start = datetime.now()

def get_session_context() -> str:
    delta = datetime.now() - _session_start
    s = int(delta.total_seconds())
    if s < 60: return "just came online"
    elif s < 3600: m = s//60; return f"online for {m} minute{'s' if m!=1 else ''}"
    else: h=s//3600; m=(s%3600)//60; return f"online for {h}h {m}m"

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
- get_account_balances: Get account balances. Args: {}
- get_spending_summary: Income vs expenses. Args: {"days": 30}
- get_spending_by_category: Spending by category. Args: {"days": 30}
- get_recent_transactions: Recent transactions. Args: {"limit": 10}
- get_unsettled_debts: Lent/borrowed amounts. Args: {}
- get_top_merchants: Top merchants by spend. Args: {"days": 30}
- read_note: Read one of your notes. Args: {"name": "note_name"}
- write_note: Create or update a note. Args: {"name": "...", "content": "...", "category": "..."}
- list_notes: See all your notes. Args: {}

EXAMPLE — correct tool use:
User: "what's in the news today?"
You: THOUGHT: I need to search for today's news.
     ACTION: {"tool": "web_search", "args": {"query": "top news today"}}
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
    elif tool_name == "read_note":
        content = get_note(args.get("name", ""))
        return content if content else "Note not found."
    elif tool_name == "write_note":
        write_note(args.get("name", ""), args.get("content", ""), args.get("category", "general"))
        return "Note saved."
    elif tool_name == "list_notes":
        notes = list_notes()
        return "\n".join(notes) if notes else "No notes yet."
    else:
        return f"Unknown tool: {tool_name}"

# ── Tool call parser ──────────────────────────────────────────────────────────
def _is_tool_call(text: str) -> dict | None:
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
def _llm(messages: list, max_tokens: int = 1024, temperature: float = 0.7) -> str:
    response = _groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    usage = response.usage
    print(f"   tokens — prompt: {usage.prompt_tokens} | completion: {usage.completion_tokens} | total: {usage.total_tokens}", flush=True)
    return response.choices[0].message.content

# ── Timing helper ─────────────────────────────────────────────────────────────
def _t(label: str, start: float):
    import time
    elapsed = time.time() - start
    print(f"⏱  {label}: {elapsed:.2f}s", flush=True)
    return time.time()

# ── Post-conversation analysis ────────────────────────────────────────────────
_ANALYSIS_PROMPT = f"""You are Mako's memory curator. Your job is to analyze a conversation
exchange and decide what to update in Mako's knowledge base.

You have access to:
- about_siddhu: permanent identity document about {USER_NAME}
- about_mako: Mako's own identity and relationship with {USER_NAME}
- current_context: what's happening in {USER_NAME}'s life right now
- topic notes: deeper notes on specific people, projects, topics

Analyze the exchange and respond in JSON only:
{{
  "save_memory": true or false,
  "memory": "concise episodic memory worth saving (or null)",
  "updates": [
    {{
      "note": "note_name",
      "action": "update|create",
      "reason": "why this note needs updating",
      "new_content": "the COMPLETE new content of the note (full rewrite, not just the change)"
    }}
  ]
}}

Rules:
- Only update notes if something genuinely new or conflicting was learned
- When updating, always rewrite the COMPLETE note — never partial patches
- Conflict resolution: if new info contradicts existing info, the new info wins
- Create a new note only if the topic is substantial enough to warrant one
- save_memory=false for small talk, weather queries, ephemeral info
- Keep note content clean, structured markdown
- Max 2 updates per exchange to avoid over-writing
"""

def _post_conversation_analysis(user_message: str, assistant_message: str):
    """
    Background analysis after each exchange.
    Updates notes and saves episodic memory if warranted.
    """
    import time
    t = time.time()

    try:
        # fetch current note contents for context
        about_siddhu  = get_note("about_siddhu") or ""
        current_ctx   = get_note("current_context") or ""

        context_block = f"""CURRENT NOTES:

=== ABOUT_SIDDHU ===
{about_siddhu[:800]}

=== CURRENT_CONTEXT ===
{current_ctx[:400]}

EXCHANGE:
{USER_NAME}: {user_message}
Mako: {assistant_message}"""

        response = _groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _ANALYSIS_PROMPT},
                {"role": "user",   "content": context_block}
            ],
            max_tokens=600,
            temperature=0.1,
        )

        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)

        # save episodic memory
        if data.get("save_memory") and data.get("memory"):
            save_memory("user", data["memory"])
            print(f"🧠 Memory saved: {data['memory'][:80]}", flush=True)

        # apply note updates
        for update in data.get("updates", []):
            note_name = update.get("note", "")
            action    = update.get("action", "update")
            content   = update.get("new_content", "")
            reason    = update.get("reason", "")

            if not note_name or not content:
                continue

            # determine category
            category = "identity" if note_name.startswith("about_") \
                else "context" if note_name == "current_context" \
                else "person" if note_name.startswith("person_") \
                else "project" if note_name.startswith("project_") \
                else "general"

            # auto_inject only for core identity notes
            auto = note_name in ("about_siddhu", "about_mako", "current_context")

            write_note(note_name, content, category=category, auto_inject=auto)
            print(f"{'📝' if action == 'update' else '✨'} Note {action}d [{note_name}]: {reason[:60]}", flush=True)

    except Exception as e:
        print(f"⚠️  Post-analysis failed ({e}), saving raw memory", flush=True)
        save_memory("user", user_message)
        save_memory("assistant", assistant_message)

    _t("4. post-analysis", t)

# ── Main think function ───────────────────────────────────────────────────────
def think(user_message: str) -> str:
    import time
    t0 = time.time()
    print(f"\n{'─'*50}", flush=True)
    print(f"🧠 think() called: {user_message[:60]}", flush=True)

    # ── 1. retrieve memories (semantic + recency split) ───────
    t = time.time()
    memories = retrieve_memories(user_message, n_semantic=5, n_recent=3)
    t = _t("1. memory retrieve", t)

    if memories:
        _emit({"type": "memory", "data": {"query": user_message[:60], "results": memories}})

    # ── 2. get auto-inject notes (about_siddhu, about_mako, current_context) ─
    t = time.time()
    identity_block = get_auto_inject_notes()
    t = _t("2. notes fetch", t)

    # ── 3. get relevant topic notes ───────────────────────────
    relevant_notes = get_relevant_notes(user_message)

    # ── 4. build system prompt ────────────────────────────────
    current_time = datetime.now().strftime("%A, %B %d %Y, %I:%M %p")
    session_ctx  = get_session_context()

    system = SYSTEM_PROMPT + TOOLS_PROMPT

    # Layer 0 — identity modules (always present)
    if identity_block:
        system += f"\n\n{'='*50}\nIDENTITY & CONTEXT\n{'='*50}\n{identity_block}"

    # Layer 1 — current time + session
    system += f"\n\n{'='*50}\nSESSION\n{'='*50}\nCurrent time: {current_time}\nSession: {session_ctx}"

    # Layer 2 — relevant topic notes (on demand)
    if relevant_notes:
        notes_block = "\n\n".join(f"=== {n['name'].upper()} ===\n{n['content']}" for n in relevant_notes)
        system += f"\n\n{'='*50}\nRELEVANT NOTES\n{'='*50}\n{notes_block}"
        print(f"   📎 Injected {len(relevant_notes)} topic note(s)", flush=True)

    # Layer 3 — semantic + recent memories
    if memories:
        memory_block = "\n".join(memories)
        system += f"\n\n{'='*50}\nRELEVANT MEMORIES\n{'='*50}\n{memory_block}"

    # Layer 4 — conversation buffer
    buffer_context = _get_buffer_context()
    if buffer_context:
        system += f"\n\n{'='*50}\nRECENT CONVERSATION\n{'='*50}\n{buffer_context}"

    print(f"   system prompt: {len(system)} chars", flush=True)

    # ── 5. emit prompt debug for inspector ────────────────────
    _emit({
        "type": "prompt_debug",
        "data": {
            "user_message": user_message,
            "sections": [
                {"label": "PERSONALITY",      "color": "blue",   "text": SYSTEM_PROMPT},
                {"label": "TOOLS",            "color": "purple", "text": TOOLS_PROMPT},
                {"label": "IDENTITY & NOTES", "color": "green",  "text": identity_block or "(none yet)"},
                {"label": "TOPIC NOTES",      "color": "amber",  "text": "\n\n".join(f"[{n['name']}]\n{n['content']}" for n in relevant_notes) or "(none relevant)"},
                {"label": "MEMORIES",         "color": "cyan",   "text": "\n".join(memories) or "(none retrieved)"},
                {"label": "BUFFER",           "color": "amber",  "text": buffer_context or "(empty)"},
                {"label": "USER MESSAGE",     "color": "red",    "text": f"[{current_time}]\n{user_message}"},
            ]
        }
    })

    # ── 6. emit user message ──────────────────────────────────
    _emit({"type": "message", "data": {"role": "user", "content": user_message}})

    # ── 7. build messages ─────────────────────────────────────
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": f"[{current_time}] {user_message}"}
    ]

    # ── 8. ReAct agentic loop ─────────────────────────────────
    MAX_TOOL_CALLS = 8
    tool_calls_made = 0
    assistant_message = ""

    while tool_calls_made < MAX_TOOL_CALLS:
        t = time.time()
        assistant_message = _llm(messages)
        t = _t(f"3. LLM call #{tool_calls_made + 1}", t)

        tool_call = _is_tool_call(assistant_message)

        if not tool_call:
            print(f"   → final answer ({len(assistant_message)} chars)", flush=True)
            break

        if 'THOUGHT:' in assistant_message:
            thought = assistant_message.split('THOUGHT:')[1].split('ACTION:')[0].strip()
            print(f"\n💭 {thought}", flush=True)
            _emit({"type": "thought", "data": {"content": thought}})

        tool_name = tool_call["tool"]
        args      = tool_call.get("args", {})

        print(f"\n🔧 Tool: {tool_name} | args: {args}", flush=True)
        _emit({"type": "tool_call", "data": {"tool": tool_name, "args": args}})

        t = time.time()
        tool_result = _run_tool(tool_name, args)
        t = _t(f"   tool: {tool_name}", t)

        _emit({"type": "tool_result", "data": {"tool": tool_name, "result": tool_result[:500]}})

        messages.append({"role": "assistant", "content": assistant_message})
        messages.append({
            "role": "user",
            "content": f"Tool result for {tool_name}:\n{tool_result}\n\nContinue your reasoning. Use another tool if needed, or give your final answer if satisfied."
        })
        tool_calls_made += 1

    # ── 9. clean + emit response ──────────────────────────────
    assistant_message = _clean_response(assistant_message)
    _emit({"type": "message", "data": {"role": "assistant", "content": assistant_message}})

    # ── 10. update buffer immediately ────────────────────────
    _add_to_buffer("user", user_message)
    _add_to_buffer("assistant", assistant_message)

    # ── 11. post-conversation analysis in background ─────────
    threading.Thread(
        target=_post_conversation_analysis,
        args=(user_message, assistant_message),
        daemon=True
    ).start()

    _t("TOTAL (excl. analysis)", t0)
    print(f"{'─'*50}\n", flush=True)

    return assistant_message