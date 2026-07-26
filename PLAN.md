# Tauon MVP Plan

## Goal

Make Tauon a small, reliable Python framework for defining tool-using agents and running them inside applications.

The MVP targets stateless, single-request workloads:

- CLI commands
- FastAPI/ASGI endpoints
- AWS Lambda handlers
- Background jobs
- One-shot automation and extraction tasks

It is intentionally **not** a conversational platform or a Flue feature-parity project.

## MVP user experience

```python
from tauon import define_agent, define_tool, run_agent, use_model, use_tool


@define_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Sunny and 22°C in {city}."


@define_agent
def WeatherAgent() -> str:
    use_model("openai/gpt-4.1-mini")
    use_tool(get_weather)
    return "You are a weather assistant."


reply = await run_agent(WeatherAgent, "What's the weather in Paris?")
```

The same agent must work from the CLI or an application:

```bash
uv run tauon run examples/weather.py --message "What's the weather in Paris?"
```

## Scope

### Included

- `define_tool` for typed sync and async Python functions
- Pydantic-backed tool argument schemas and validation
- `define_agent` for zero-required-argument agent functions
- `use_model` and `use_tool` render hooks
- Provider/model resolution through Tau's catalog
- One-shot async `run_agent`
- Multi-step tool-call execution through Tau's `AgentHarness`
- Final assistant text returned as `str`
- Minimal CLI runner
- Usage in FastAPI, Lambda, and other Python hosts

### Explicitly deferred

- Persistent sessions and conversation history
- Database or filesystem persistence
- Sandboxes and arbitrary code execution environments
- Skills and skill discovery
- Subagents and delegation
- MCP servers
- Channels and webhooks
- Durable recovery and job orchestration
- Built-in observability integrations
- Client SDKs
- Framework-specific deployment adapters
- CLI streaming output
- Multiple providers in one runtime

## Current architecture

```text
Agent function
  -> collect_frame()
      -> model, tools, instructions
  -> run_agent()
      -> resolve provider and model
      -> build system prompt
      -> create tau_agent.AgentHarness
      -> stream model events
      -> execute tool calls
      -> return assistant text
```

Tauon stays a thin layer over `tau-ai`:

- `tau_agent.AgentHarness` manages model/tool turns.
- `tau_agent.AgentTool` represents tools.
- `tau_coding` resolves configured providers and models.
- Pydantic generates and validates tool schemas.
- Tauon owns the user-facing decorators, render hooks, prompt assembly, and CLI.

Rendering is synchronous; execution is asynchronous. Each `run_agent()` call starts with a fresh frame and empty message history.

## tau-ai SDK boundary

`tau-ai` (the umbrella for `tau_agent`, `tau_ai`, `tau_coding`) is working toward a
stable public SDK. Until that SDK is released, Tauon imports directly from those
packages.

**Strategy when the SDK lands:** all imports are updated in-place across the ~6 files
that currently reference `tau_*` packages (`agent.py`, `tool.py`, `provider.py`,
`hooks.py`, `_types.py`, `tests/conftest.py`). This is a mechanical,
grep-able find-and-replace — no adapter layer or re-export module is added now
because the SDK's actual API shape is unknown.

Keeping this coupling visible (not hidden behind an abstraction) means the SDK
adoption is a straightforward rename pass, not a rewrite of adapters that guessed
wrong.

## Public API

```python
from tauon import define_agent, define_tool, run_agent, use_model, use_tool
```

### `define_tool`

`define_tool(fn)` should:

- Use the function name as the tool name and label.
- Use the first docstring paragraph as the description.
- Preserve later docstring paragraphs as an optional prompt snippet.
- Generate a JSON schema from the function signature.
- Validate model arguments before calling the function.
- Support sync and async functions.
- Convert the return value to `str` for the MVP.
- Reject unsupported signatures with a clear error.
- Reject duplicate tool names during agent rendering.

### `define_agent`

`define_agent(fn)` should:

- Require no required positional or keyword parameters.
- Preserve the original callable so it remains importable and callable.
- Mark the function for CLI discovery.
- Return clear errors for invalid definitions.

Agent functions return `str | None`, which becomes the instruction text.

### `use_model` and `use_tool`

Hooks are valid only while an agent is rendering:

- `use_model(model: str)` sets the model for the current frame.
- `use_tool(tool: AgentTool)` registers a tool.
- Calling either hook outside an agent render raises a clear `RuntimeError`.
- A fresh frame is created for every render.

### `run_agent`

`run_agent` should:

- Collect the agent render frame.
- Require a model from `use_model()` or `model=`.
- Allow `model=` to override the rendered model.
- Support `provider/model` model syntax.
- Accept an injected provider for tests and advanced integrations.
- Resolve default providers through Tau's catalog.
- Build a minimal system prompt from instructions and tools.
- Run Tau's harness and complete tool-call turns.
- Return the final assistant text.
- Surface provider and tool errors instead of silently returning empty output.
- Close providers created by Tauon.
- Expose a bounded timeout and cancellation path where supported by Tau.
- Prevent unbounded agent/tool turns.

Keep the return type as `str`; do not add a response wrapper until real use cases require metadata or usage information.

## Provider behavior

`default_provider` should:

- Resolve known providers and models through Tau's built-in catalog.
- Support model specs such as `openai/gpt-4.1-mini`.
- Read credentials from environment variables such as `OPENAI_API_KEY`.
- Support explicit `api_key` and `base_url` overrides.
- Use the OpenAI-compatible fallback only for explicit overrides or unresolved catalog models.
- Produce actionable errors for missing credentials and invalid provider/model selections.

## CLI

Support:

```bash
tauon run <path> --message <message> [--model <model>] [--provider <provider>]
```

The CLI should:

- Load a Python module from the supplied path.
- Find the first callable marked by `define_agent`.
- Run it with AnyIO.
- Print only the final assistant text.
- Report missing agents and load failures clearly.

Streaming output and tool-call display remain deferred.

## Integration examples

Add short, tested examples for:

### FastAPI

```python
@app.post("/chat")
async def chat(message: str) -> dict[str, str]:
    return {"reply": await run_agent(MyAgent, message)}
```

### AWS Lambda

```python
import asyncio


def lambda_handler(event, context):
    reply = asyncio.run(run_agent(MyAgent, event["message"]))
    return {"statusCode": 200, "body": reply}
```

Document:

- Provider API key environment variables.
- Outbound network requirements.
- Lambda timeout and package/container deployment.
- The stateless nature of each invocation.
- The need for users to provide their own persistence if they need sessions.

## Reliability work before release

Prioritize these gaps in the current implementation:

1. Resolve postponed annotations when building tool schemas.
2. Validate and reject unsupported tool signatures.
3. Detect duplicate tools during an agent render.
4. Add timeout, cancellation, and maximum-turn handling using Tau's supported APIs.
5. Improve errors for invalid models, missing keys, tool validation failures, and provider failures.
6. Verify provider cleanup on success, tool errors, cancellation, and provider errors.

Avoid adding abstractions that do not support one of these MVP workflows.

## Tests

Maintain tests for:

- Tool schema generation and required/default parameters.
- Sync and async tool execution.
- Invalid tool arguments.
- Docstring description and prompt snippet handling.
- Unsupported tool signatures.
- Agent signature validation and CLI discovery.
- Hook failures outside an agent render.
- Frame collection, model overrides, and duplicate tools.
- Provider/model resolution.
- Provider errors and cleanup.
- Tool-call execution through a fake provider.
- Timeout, cancellation, and turn limits.
- FastAPI/Lambda integration examples where practical.

## Quality gates

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty
uv build
```

The MVP is ready when a new user can install the package, define one agent and one tool, run it locally, and embed the same agent in an async web endpoint or Lambda without reading Tau internals.

## Post-MVP candidates

Only after the stateless runner is stable, consider:

1. A `Session` abstraction with caller-owned persistence.
2. A streaming API for SSE and interactive clients.
3. Structured response metadata such as usage and tool-call traces.
4. Optional observability hooks.
5. Additional integrations driven by real user demand.
