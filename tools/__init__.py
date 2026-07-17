# tools/__init__.py — importing this package registers every tool.
from tools.registry import get_specs, run_tool  # noqa: F401
from tools import search, weather, system, finance, notes, memory  # noqa: F401
