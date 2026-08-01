"""Agent definition and execution."""

from __future__ import annotations

import asyncio
import inspect
from typing import cast

from tau_agent.events import MessageEndEvent, MessageUpdateEvent
from tau_agent.harness import AgentHarness, AgentHarnessConfig
from tau_agent.messages import AssistantMessage
from tau_agent.provider import ModelProvider
from tau_agent.provider_events import TextDeltaEvent

from tauon._prompt import build_system_prompt
from tauon._types import Agent, AgentFn
from tauon.hooks import collect_frame
from tauon.provider import _split_model_spec, default_provider


def define_agent(fn: AgentFn) -> Agent:
    """Decorator that turns a plain (sync) function into a Tauon agent."""
    name = fn.__name__
    if inspect.iscoroutinefunction(fn):
        msg = (
            f"Agent function {name!r} must be a plain (sync) function; "
            "async agent functions are not supported"
        )
        raise TypeError(msg)
    sig = inspect.signature(fn)
    for _name, param in sig.parameters.items():
        if param.default is inspect.Parameter.empty and param.kind in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }:
            msg = f"Agent function {fn.__name__!r} must not have required parameters"
            raise TypeError(msg)
    agent = cast(Agent, fn)
    agent._tauon_agent = True
    return agent


async def run_agent(
    agent: Agent,
    message: str,
    *,
    provider: ModelProvider | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    provider_name: str | None = None,
    max_turns: int | None = 25,
    timeout: float | None = None,
) -> str:
    """Run one agent with one user message and return the assistant text.

    Parameters
    ----------
    agent:
        Agent function defined with ``@define_agent``.
    message:
        User message to send.
    provider:
        Injected provider (for tests / advanced usage).  When omitted Tau's
        built-in catalog is used to resolve *provider_name* / *model*.
    api_key:
        Override the provider API key.
    base_url:
        Override the provider base URL.
    model:
        Override the model set by ``use_model()`` inside the agent.
        When set, ``model=`` wins over ``use_model()``.
        Supports ``provider/model`` syntax.
    provider_name:
        Provider name override (e.g. ``"openai"``, ``"anthropic"``).
    max_turns:
        Maximum tool-call turns before the agent is stopped.
        ``None`` disables the limit.
    timeout:
        Maximum total wall-clock seconds before ``asyncio.TimeoutError``
        is raised.  ``None`` disables the limit.

    Returns
    -------
    Final assistant text.  With multi-turn tool use, this is the text of the
    final assistant message (intermediate reasoning prose is not included).

    Raises
    ------
    RuntimeError
        When the model stops with an error (including ``max_turns`` being
        reached) or the provider raises a transport error.
    """
    frame = collect_frame(agent)
    raw_model = model or frame.model
    if not raw_model:
        msg = "No model specified. Call use_model() in the agent or pass model=."
        raise RuntimeError(msg)

    parsed_provider, resolved_model = _split_model_spec(raw_model)
    if provider_name is None:
        provider_name = parsed_provider

    close_provider = provider is None
    if provider is None:
        provider = default_provider(
            api_key=api_key,
            base_url=base_url,
            model=resolved_model,
            provider_name=provider_name,
        )

    system = build_system_prompt(frame)
    harness = AgentHarness(
        config=AgentHarnessConfig(
            provider=provider,
            model=resolved_model,
            system=system,
            tools=frame.tools,
            max_turns=max_turns,
        )
    )

    try:
        text_parts: list[str] = []
        last_assistant: AssistantMessage | None = None

        async def _run() -> str:
            nonlocal text_parts, last_assistant
            async for event in harness.prompt(message):
                if isinstance(event, MessageUpdateEvent):
                    inner = event.assistant_message_event
                    if isinstance(inner, TextDeltaEvent):
                        text_parts.append(inner.delta)
                elif isinstance(event, MessageEndEvent) and isinstance(
                    event.message, AssistantMessage
                ):
                    last_assistant = event.message
            if last_assistant is not None and last_assistant.error_message:
                raise RuntimeError(last_assistant.error_message)
            if last_assistant is not None and last_assistant.text:
                # Authoritative assembled text of the final assistant message.
                return last_assistant.text
            # Defensive: provider emitted no final message with text.
            return "".join(text_parts)

        if timeout is not None:
            return await asyncio.wait_for(_run(), timeout=timeout)
        return await _run()
    except (RuntimeError, TimeoutError):
        # Keep our own errors and timeout semantics intact; re-raise as-is.
        raise
    except Exception as exc:
        # The harness isolates tool failures; anything else is transport-level.
        msg = f"Provider error: {exc}"
        raise RuntimeError(msg) from exc
    finally:
        if close_provider:
            aclose = getattr(provider, "aclose", None)
            if aclose is not None:
                await aclose()


__all__ = ["Agent", "define_agent", "run_agent"]
