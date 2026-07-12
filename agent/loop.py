# agent/loop.py — the agentic loop.
#
# Two wire formats, one loop:
#   - native: structured tool calls via the provider's API (preferred)
#   - react:  THOUGHT/ACTION text parsing for models without tool support
# Which one runs is decided by the "chat" route's native_tools flag.

import time
from config import MAX_TOOL_CALLS
from llm import complete
from llm.client import assistant_tool_call_message, tool_result_message
from llm.react_fallback import parse_react, extract_thought, clean_response
from tools.registry import run_tool
from agent.events import emit


def run_agent_loop(messages: list[dict], tool_specs: list[dict] | None) -> str:
    """
    Run the loop until the model produces a final answer.
    `tool_specs` present → native tool calling; None → ReAct fallback.
    Mutates `messages` in place; returns the final answer text.
    """
    calls_made = 0

    while True:
        t = time.time()
        response = complete(messages, tools=tool_specs, role="chat")
        print(f"⏱  LLM call #{calls_made + 1}: {time.time() - t:.2f}s", flush=True)

        if tool_specs is not None:
            # ── native path ────────────────────────────────
            if not response.has_tool_calls or calls_made >= MAX_TOOL_CALLS:
                # at the cap the model may have answered with only tool calls —
                # never return an empty reply
                return response.text.strip() or \
                    "I got a bit lost in my tools there — mind asking that again?"

            if response.text.strip():
                emit({"type": "thought", "data": {"content": response.text.strip()}})

            messages.append(assistant_tool_call_message(response.text, response.tool_calls))
            for tc in response.tool_calls:
                result = _execute(tc.name, tc.args)
                messages.append(tool_result_message(tc, result))
                calls_made += 1
        else:
            # ── ReAct fallback path ────────────────────────
            tool_call = parse_react(response.text)
            if not tool_call or calls_made >= MAX_TOOL_CALLS:
                return clean_response(response.text) or \
                    "I got a bit lost in my tools there — mind asking that again?"

            thought = extract_thought(response.text)
            if thought:
                print(f"💭 {thought}", flush=True)
                emit({"type": "thought", "data": {"content": thought}})

            result = _execute(tool_call.name, tool_call.args)
            messages.append({"role": "assistant", "content": response.text})
            messages.append({
                "role": "user",
                "content": f"Tool result for {tool_call.name}:\n{result}\n\n"
                           "Continue your reasoning. Use another tool if needed, "
                           "or give your final answer if satisfied.",
            })
            calls_made += 1


def _execute(name: str, args: dict) -> str:
    print(f"🔧 Tool: {name} | args: {args}", flush=True)
    emit({"type": "tool_call", "data": {"tool": name, "args": args}})

    t = time.time()
    result = run_tool(name, args)
    print(f"⏱  tool {name}: {time.time() - t:.2f}s", flush=True)

    emit({"type": "tool_result", "data": {"tool": name, "result": result[:500]}})
    return result
