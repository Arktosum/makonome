# llm/react_fallback.py — text-based ReAct tool calling for models WITHOUT
# native tool support. The agent loop uses this path automatically when the
# active route has native_tools=False. Same tools, same loop — just a
# different wire format.

import json
from llm.client import ToolCall

REACT_HEADER = """
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
7. Never expose THOUGHT, ACTION, or FINAL ANSWER markers to the user.

AVAILABLE TOOLS:
"""


def build_react_prompt(tool_specs: list[dict]) -> str:
    """Generate the ReAct tools prompt from registry specs."""
    lines = []
    for t in tool_specs:
        props = t["input_schema"].get("properties", {})
        args_example = {k: v.get("description", v.get("type", "...")) for k, v in props.items()}
        lines.append(f'- {t["name"]}: {t["description"]} Args: {json.dumps(args_example)}')
    return REACT_HEADER + "\n".join(lines)


def parse_react(text: str) -> ToolCall | None:
    """Extract a tool call from a ReAct-formatted response, if present."""
    candidates = []
    if "ACTION:" in text:
        candidates.append(text.split("ACTION:")[-1])
    candidates.append(text)

    for chunk in candidates:
        try:
            chunk = chunk.strip()
            start = chunk.index("{")
            end = chunk.rindex("}") + 1
            data = json.loads(chunk[start:end])
            if "tool" in data:
                return ToolCall(id="react", name=data["tool"], args=data.get("args", {}))
        except (ValueError, json.JSONDecodeError):
            continue
    return None


def extract_thought(text: str) -> str | None:
    if "THOUGHT:" in text:
        return text.split("THOUGHT:")[1].split("ACTION:")[0].strip()
    return None


def clean_response(text: str) -> str:
    """Strip any leaked ReAct markers from a final answer."""
    clean = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("THOUGHT:") or stripped.startswith("ACTION:"):
            continue
        if stripped.startswith("FINAL ANSWER:"):
            clean.append(line.split("FINAL ANSWER:", 1)[-1].strip())
            continue
        clean.append(line)
    return "\n".join(clean).strip()
