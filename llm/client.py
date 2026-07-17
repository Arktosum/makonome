# llm/client.py — provider-agnostic LLM adapter.
#
# One entry point: complete(messages, tools=None, role="chat").
# Messages use OpenAI chat format internally:
#   {"role": "system"|"user"|"assistant"|"tool", "content": str, ...}
#   assistant tool-call turns carry "tool_calls"; tool results carry "tool_call_id".
# The Anthropic driver converts to/from that format transparently.

import os
import json
from dataclasses import dataclass, field
from dotenv import load_dotenv
from config import MODEL_ROUTES

load_dotenv()


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


# ── Lazy provider clients ─────────────────────────────────────────────────────
# Cached per (provider, base_url, key_env) so any number of OpenAI-compatible
# providers can coexist — each route may carry its own base_url/api_key_env.
_clients: dict = {}


def _client_for(route: dict):
    provider = route["provider"]
    base_url = route.get("base_url") or (
        os.getenv("LLM_BASE_URL") if provider == "openai_compatible" else None)
    key_env = route.get("api_key_env")
    cache_key = (provider, base_url, key_env)
    if cache_key in _clients:
        return _clients[cache_key]

    def _key(default_env: str, fallback: str | None = None):
        return os.getenv(key_env) if key_env else (os.getenv(default_env) or fallback)

    if provider == "groq":
        from groq import Groq
        client = Groq(api_key=_key("GROQ_API_KEY"))
    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=_key("OPENAI_API_KEY"))
    elif provider == "openai_compatible":
        from openai import OpenAI
        client = OpenAI(base_url=base_url, api_key=_key("LLM_API_KEY", "not-needed"))
    elif provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=_key("ANTHROPIC_API_KEY"))
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    _clients[cache_key] = client
    return client


# ── Public API ────────────────────────────────────────────────────────────────

def route_supports_native_tools(role: str) -> bool:
    return MODEL_ROUTES[role].get("native_tools", False)


def complete(messages: list[dict], tools: list[dict] | None = None,
             role: str = "chat", max_tokens: int | None = None,
             temperature: float | None = None) -> LLMResponse:
    """
    Run one completion on whatever model the given role routes to.
    `tools` is a list of specs: {"name", "description", "input_schema"}.
    If the route defines a "fallback", provider failures (rate limits,
    outages) retry once there instead of breaking the caller.
    """
    route = MODEL_ROUTES[role]
    try:
        return _complete_route(route, messages, tools, max_tokens, temperature)
    except Exception as e:
        fb = route.get("fallback")
        if not fb:
            raise
        print(f"⚠️  [{role}] {route['provider']}/{route['model']} failed ({e}) "
              f"— falling back to {fb['provider']}/{fb['model']}", flush=True)
        fb_route = {**route, **fb, "fallback": None}
        return _complete_route(fb_route, messages, tools, max_tokens, temperature)


def _complete_route(route: dict, messages: list[dict], tools: list[dict] | None,
                    max_tokens: int | None, temperature: float | None) -> LLMResponse:
    provider = route["provider"]
    kwargs = {
        "model": route["model"],
        "max_tokens": max_tokens or route.get("max_tokens", 1024),
        "temperature": temperature if temperature is not None else route.get("temperature", 1.0),
    }
    if tools and not route.get("native_tools", False):
        tools = None  # caller handles the ReAct fallback path

    if provider == "anthropic":
        resp = _complete_anthropic(route, messages, tools, kwargs)
    else:  # groq / openai / openai_compatible all speak the OpenAI protocol
        resp = _complete_openai(route, messages, tools, kwargs)

    if resp.usage:
        print(f"   tokens — prompt: {resp.usage.get('prompt', '?')} | "
              f"completion: {resp.usage.get('completion', '?')} | "
              f"total: {resp.usage.get('total', '?')}", flush=True)
    return resp


# ── OpenAI-protocol driver (groq, openai, openai_compatible) ─────────────────

def _complete_openai(route: dict, messages: list[dict],
                     tools: list[dict] | None, kwargs: dict) -> LLMResponse:
    client = _client_for(route)

    api_kwargs = dict(kwargs, messages=messages)
    if tools:
        api_kwargs["tools"] = [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        } for t in tools]

    response = client.chat.completions.create(**api_kwargs)
    choice = response.choices[0].message

    tool_calls = []
    for tc in (choice.tool_calls or []):
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, args=args))

    usage = {}
    if response.usage:
        usage = {
            "prompt": response.usage.prompt_tokens,
            "completion": response.usage.completion_tokens,
            "total": response.usage.total_tokens,
        }

    return LLMResponse(text=choice.content or "", tool_calls=tool_calls, usage=usage)


def assistant_tool_call_message(text: str, tool_calls: list[ToolCall]) -> dict:
    """Build the assistant turn that records native tool calls (OpenAI format)."""
    return {
        "role": "assistant",
        "content": text or None,
        "tool_calls": [{
            "id": tc.id,
            "type": "function",
            "function": {"name": tc.name, "arguments": json.dumps(tc.args)},
        } for tc in tool_calls],
    }


def tool_result_message(tool_call: ToolCall, result: str) -> dict:
    """Build the tool-result turn (OpenAI format)."""
    return {"role": "tool", "tool_call_id": tool_call.id, "content": result}


# ── Anthropic driver ──────────────────────────────────────────────────────────

def _complete_anthropic(route: dict, messages: list[dict], tools: list[dict] | None,
                        kwargs: dict) -> LLMResponse:
    client = _client_for(route)

    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    converted = []
    for m in messages:
        if m["role"] == "system":
            continue
        if m["role"] == "tool":
            converted.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": m["tool_call_id"],
                    "content": m["content"],
                }],
            })
        elif m["role"] == "assistant" and m.get("tool_calls"):
            blocks = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m["tool_calls"]:
                blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "input": json.loads(tc["function"]["arguments"] or "{}"),
                })
            converted.append({"role": "assistant", "content": blocks})
        else:
            converted.append({"role": m["role"], "content": m["content"]})

    api_kwargs = {
        "model": kwargs["model"],
        "max_tokens": kwargs["max_tokens"],
        "temperature": min(kwargs.get("temperature", 1.0), 1.0),
        "system": system,
        "messages": converted,
    }
    if tools:
        api_kwargs["tools"] = [{
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        } for t in tools]

    response = client.messages.create(**api_kwargs)

    text_parts, tool_calls = [], []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(ToolCall(id=block.id, name=block.name, args=block.input))

    usage = {
        "prompt": response.usage.input_tokens,
        "completion": response.usage.output_tokens,
        "total": response.usage.input_tokens + response.usage.output_tokens,
    }
    return LLMResponse(text="\n".join(text_parts), tool_calls=tool_calls, usage=usage)
