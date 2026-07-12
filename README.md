# Mako (makonome)

My very own JARVIS-inspired personal AI assistant — with long-term memory,
a personality that evolves through lived experience, and the good sense to
text first only when she has a reason to.

## What she does

- **Remembers.** Episodic memories (semantic + recency retrieval via Supabase
  pgvector) plus a curated notes knowledge base: `about_siddhu`,
  `current_context`, `open_threads`, and one `person_*` note per person in
  my life.
- **Learns who she is.** After meaningful conversations a background curator
  writes one first-person line to her journal. Weekly, a reflection pass reads
  the journal and rewrites `about_mako` — her identity is emergent, not
  hardcoded. The prompt in `config.py` is only the seed.
- **Texts first, rarely.** A heartbeat scheduler ticks every 15 minutes behind
  hard gates (quiet hours, 3h min silence, 4h spacing, 3/day cap) and only then
  asks the model if there's genuinely something worth saying. SILENT is the
  expected answer.
- **Uses tools.** Web search, page fetch, weather, app launching, personal
  finance (BalanceFlow), and her own notes — all registered once in
  `tools/registry.py`.

## Architecture

```
main.py               entry point (local CLI + dashboard, or cloud)
config.py             model routing, persona seed, heartbeat settings
llm/                  provider adapter — groq / openai / anthropic /
                      openai-compatible; native tool calling with ReAct
                      text fallback for models without tool support
agent/                Session (buffer, thread-safe think), context assembly,
                      agentic loop, dashboard event emission
tools/                @tool registry + implementations
memory/               Supabase episodic memory, notes system, curator
life/                 wakeup message, heartbeat scheduler, self-reflection
dashboard/            Flask + WebSocket dashboard with prompt inspector
mobile/               Flutter app (talks to the same API)
```

Model-agnostic by design: every job (chat / curator / wakeup / heartbeat /
reflection) routes independently in `config.py`'s `MODEL_ROUTES` — swap any
role to a different provider with one line.

## Running

```
pip install -r requirements.txt
python main.py            # dashboard at http://localhost:8765
```

Deploys to Render via `render.yaml` (`RENDER` env var switches to cloud mode).

### Environment (.env)

| var | purpose |
|-----|---------|
| `GROQ_API_KEY` | default LLM provider |
| `VECTORDB_SUPABASE_URL` / `VECTORDB_SUPABASE_ANON_KEY` | memory store |
| `BALANCEFLOW_SUPABASE_URL` / `BALANCEFLOW_SUPABASE_ANON_KEY` | finance tools |
| `MAKO_DASH_TOKEN` | shared-secret auth (recommended in cloud) |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `LLM_BASE_URL` + `LLM_API_KEY` | optional alternate providers |

## API

**`POST /api/chat`** — synchronous chat for external apps.

```
POST /api/chat
Authorization: Bearer <MAKO_DASH_TOKEN>     (or X-Mako-Token, or ?token=)
{"message": "...", "source": "mobile"}

→ {"ok": true, "reply": "...", "time": "..."}
```

**`WS /ws?token=...`** — live event stream (messages, thoughts, tool calls,
memory hits, heartbeat decisions, prompt-inspector breakdowns). Send
`{"type": "user_message", "content": "..."}`.

**`POST /api/clear-memories`** — wipe episodic memory (same auth).

One Session backs every door, so Mako is one continuous conversation across
dashboard, terminal, and API.
