# tools/registry.py — single source of truth for Mako's tools.
#
# Register a tool once with @tool(...) and it automatically becomes:
#   - a native tool spec for providers with structured tool calling
#   - a line in the generated ReAct prompt for providers without it
#   - dispatchable via run_tool(name, args)

import inspect

_REGISTRY: dict[str, dict] = {}


def tool(description: str, params: dict | None = None, required: list[str] | None = None):
    """
    Decorator. `params` is a dict of JSON-schema properties, e.g.
        {"query": {"type": "string", "description": "search query"}}
    If omitted, the tool takes no arguments.
    """
    def decorator(fn):
        props = params or {}
        req = required if required is not None else list(props.keys())
        _REGISTRY[fn.__name__] = {
            "fn": fn,
            "spec": {
                "name": fn.__name__,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": props,
                    "required": req,
                },
            },
        }
        return fn
    return decorator


def get_specs() -> list[dict]:
    return [entry["spec"] for entry in _REGISTRY.values()]


def run_tool(name: str, args: dict) -> str:
    entry = _REGISTRY.get(name)
    if not entry:
        return f"Unknown tool: {name}"
    try:
        fn = entry["fn"]
        # drop unexpected args so a hallucinated extra key doesn't crash the call
        sig = inspect.signature(fn)
        accepted = {k: v for k, v in (args or {}).items() if k in sig.parameters}
        result = fn(**accepted)
        return str(result)
    except Exception as e:
        return f"Tool {name} failed: {e}"
