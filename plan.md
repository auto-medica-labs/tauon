# Tauon Plan — Weather Agent Milestone

## Goal

Build the first usable version of `tauon`: a Python package that lets users define agents and tools, then run them via CLI or import them into apps like FastAPI.

This milestone is intentionally small:

- `define_tool` — turn a typed Python function into an agent tool
- `define_agent` — turn a Python function into an agent
- `use_model` / `use_tool` — hooks used inside an agent body
- `run_agent` — run one agent with one user message
- `tauon run` — CLI entry point
- Provider resolution via Tau's built-in catalog

No sandboxes, no skills, no subagents, no persistence, no channels.

## Toolchain

- **Package manager / runner:** `uv`
- **Build backend:** `hatchling`
- **Type checker:** `ty` (not mypy)
- **Linter / formatter:** `ruff`
- **Test runner:** `pytest`
- **Target Python:** `>=3.12`

## Dependencies

- `tau-ai` — PyPI version, includes `tau_agent`, `tau_ai`, and `tau_coding`
- `pydantic` — pulled in by tau-ai, used for tool schema generation
- `typer` — pulled in by tau-ai, used for the CLI

FastAPI is not a dependency of tauon itself; users add it in their own apps.

## Project layout

```
tauon/
├── plan.md
├── pyproject.toml
├── README.md
├── examples/
│   └── weather.py
├── src/
│   └── tauon/
│       ├── __init__.py
│       ├── _types.py
│       ├── _prompt.py
│       ├── agent.py
│       ├── cli.py
│       ├── hooks.py
│       ├── provider.py
│       └── tool.py
└── tests/
    ├── conftest.py
    ├── test_agent.py
    ├── test_run_agent.py
    └── test_tool.py
```

## Public API

```python
from tauon import define_agent, define_tool, run_agent, use_model, use_tool
```

### Example: weather agent

```python
# examples/weather.py
from tauon import define_agent, define_tool, use_model, use_tool


@define_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    # Real implementation would call a weather API.
    return f"Sunny and 22°C in {city}."


@define_agent
def WeatherAgent() -> str:
    use_model("gpt-5.6-luna")
    use_tool(get_weather)
    return (
        "You are a weather assistant. "
        "When the user asks about the weather, call the get_weather tool with the city name."
    )
```

```bash
export OPENAI_API_KEY=...
uv run tauon run examples/weather.py --message "What's the weather in Paris?"
```

```python
# FastAPI example (user's app, not in tauon)
from fastapi import FastAPI
from tauon import run_agent
from examples.weather import WeatherAgent

app = FastAPI()

@app.post("/weather")
async def weather(message: str) -> dict[str, str]:
    reply = await run_agent(WeatherAgent, message=message)
    return {"reply": reply}
```

## Module responsibilities

### `tauon.tool`

`define_tool(fn)`:

- Inspect `fn.__name__` for the tool name.
- Inspect `fn.__doc__` for description and `prompt_snippet`.
- Build a Pydantic model from the function signature using `pydantic.create_model`.
- Generate JSON Schema via `model.model_json_schema()`.
- Return an `AgentTool` compatible with `tau_agent.AgentHarness`.
- `execute_fn` parses arguments, calls `fn`, and wraps the return value in `AgentToolResult`.
- Support sync and async `fn`.
- Coerce return value to `str` with `str()` for the first version.

Type discipline: the returned object must be typed strongly enough that `use_tool` accepts it without `Any` leakage.

### `tauon.hooks`

- `RenderFrame` dataclass: `model: str | None`, `tools: list[AgentTool]`, `instructions: str | None`.
- `current_frame: ContextVar[RenderFrame | None]`.
- `use_model(model: str) -> None` — sets frame.model.
- `use_tool(tool: AgentTool) -> None` — appends to frame.tools.
- `collect_frame(agent_fn: Callable[[], str | None]) -> RenderFrame` — runs the function inside a fresh frame and returns the collected frame.
- Hooks must raise clear errors when called outside an agent render.

### `tauon.agent`

`Agent` protocol:

- Callable with no required arguments.
- Returns `str | None`.
- Carries a `_tauon_agent: Literal[True]` marker.

`define_agent(fn) -> Agent`:

- Decorator that validates the signature and tags the function.
- Returns the original function unchanged so it can still be imported and called normally.

`run_agent(agent, message, *, provider=None, api_key=None, base_url=None, model=None, provider_name=None) -> str`:

- Collect the render frame by calling `agent()`.
- Ensure `frame.model` is set; allow `model` kwarg to override it.
- Parse `provider/model` syntax from the model specifier.
- Build a system prompt from the agent's returned instructions and tool list.
- Create a provider via Tau's catalog if no `provider` is given.
- Create an `AgentHarness` with the bare model name, tools, and system prompt.
- Stream `harness.prompt(message)`, collect assistant text.
- Surface provider errors instead of returning empty strings.
- Return final assistant text.
- Close provider if tauon created it.
- Be fully async so it can be awaited inside FastAPI, Starlette, or any ASGI app.

### `tauon._prompt`

Minimal system prompt builder:

```text
<instructions>
{agent-returned string}
</instructions>

<tools>
- get_weather: Get the current weather for a city.
</tools>
```

Kept internal; may be replaced later without changing public API.

### `tauon.provider`

`default_provider(*, api_key=None, base_url=None, model=None, provider_name=None) -> ModelProvider`:

- Use `tau_coding.provider_config.ProviderSettings` and `resolve_provider_selection` to resolve the provider and model the same way Tau does.
- Support `provider/model` syntax (e.g. `openai/gpt-5.6-luna`, `anthropic/claude-sonnet-4-6`).
- Create the runtime provider with `tau_coding.provider_runtime.create_model_provider`.
- Fall back to a plain `OpenAICompatibleProvider` only when explicit `api_key` or `base_url` overrides are given.
- Reads API keys from environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) via the catalog runtime.

The provider object is closable; `run_agent` must close it when it creates it.

### `tauon.cli`

`tauon run <path> --message <message> [--model <model>] [--provider <provider>]`:

- Load the module at `<path>`.
- Find the first object tagged by `define_agent`.
- Call `run_agent(agent, message, model=model, provider_name=provider)`.
- Print the returned text.

### `tauon._types`

Internal shared types:

- `JSONValue`
- `ToolExecutor`
- `Agent` protocol refinements

## Type discipline

- All public functions are fully typed.
- `ty` is run in strict mode in CI.
- No `Any` in public signatures unless absolutely necessary.
- Tool schema generation keeps type information as long as possible using Pydantic generics.
- `run_agent` returns `str`, not `Any`.

## Tests

- `test_tool.py`: schema generation, sync/async execution, docstring handling.
- `test_agent.py`: frame collection, missing-model errors, duplicate-tool errors.
- `test_run_agent.py`: fake `ModelProvider` that exercises the full tool-call path.
- `conftest.py`: shared fixtures (fake provider, fake weather tool).

## Build / check commands

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty
```

## Out of scope

- Sandboxes (`read`/`write`/`bash`)
- Skills and skill discovery
- Subagents and `task` delegation
- MCP servers
- Channels / webhooks
- Durable sessions or persistence
- Streaming output in CLI
- Multiple providers in one runtime

## Future: sessions and FastAPI

`run_agent` is currently single-turn and stateless. Each call starts with an empty message list, so follow-up questions have no memory.

Reference implementation: Flue (`../flue`) builds sessions on top of Pi's `Agent` loop from `@earendil-works/pi-agent-core`:

```ts
this.agentLoop = new Agent({
  initialState: { systemPrompt, model, tools, messages: [], thinkingLevel },
  streamFn: ...,         // provider call
  toolExecution: 'parallel',
  steeringMode: 'all',   // queue user messages, drain at next turn
  followUpMode: 'all',
  prepareNextTurn: ...,  // re-render tools/prompt each turn
});

this.agentLoop.steer(userMessage);
this.agentLoop.continue();
```

The loop persists `messages` across turns, handles multi-turn tool cycles, and emits events that Flue records.

For tauon, the equivalent Python building blocks are `tau_agent.loop.Agent` or `tau_agent.harness.AgentHarness` plus a stored message list. A minimal session API could look like:

```python
from tauon import Session

session = Session(WeatherAgent)
reply1 = await session.prompt("What's the weather in Paris?")
reply2 = await session.prompt("What about Bangkok?")  # remembers Paris context
```

Or in FastAPI:

```python
from fastapi import FastAPI
from tauon import Session

app = FastAPI()
sessions: dict[str, Session] = {}

@app.post("/chat/{session_id}")
async def chat(session_id: str, message: str):
    session = sessions.setdefault(session_id, Session(WeatherAgent))
    reply = await session.prompt(message)
    return {"reply": reply}
```

Open design questions for the session feature:

1. Should sessions be in-memory only, or pluggable persistence?
2. Should the agent function re-render each turn (so `use_tool`/`use_model` can change), or freeze at session creation?
3. Should streaming be supported via SSE before or after sessions?
4. Should sessions be a separate import (`from tauon import Session`) or an option in `run_agent`?


## Open decisions

1. Should `define_tool` coerce any return value to `str` or require `str`?  
   **Decision:** coerce with `str()` for the first version.
2. Should CLI print tool calls as they happen?  
   **Decision:** no, print only the final assistant text.
3. Should `run_agent` accept a `system` override?  
   **Decision:** not in this milestone; the agent function owns instructions.
