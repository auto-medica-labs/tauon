"""Tests for running agents with a fake provider."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
from tau_agent.messages import AssistantMessage, TextContent, ToolCall
from tau_agent.provider import CancellationToken
from tau_agent.provider_events import AssistantDoneEvent, AssistantStartEvent, TextDeltaEvent
from tau_ai.events import AssistantMessageEvent

from conftest import FakeProvider
from tauon import define_agent, define_tool, use_model, use_prompt, use_tool
from tauon.agent import run_agent


@define_tool
def local_weather(city: str) -> str:
    """Get local weather."""
    return f"Local weather in {city}"


@pytest.mark.anyio
async def test_run_agent_requires_model() -> None:
    @define_agent
    def NoModelAgent() -> str:
        return "instructions"

    with pytest.raises(RuntimeError, match="No model"):
        await run_agent(NoModelAgent, "hi")


@pytest.mark.anyio
async def test_run_agent_returns_provider_text() -> None:
    @define_agent
    def EchoAgent() -> str:
        use_model("test/model")
        return "Echo."

    provider = FakeProvider(reply="hello world")
    result = await run_agent(EchoAgent, "hi", provider=provider)
    assert result == "hello world"


@pytest.mark.anyio
async def test_run_agent_executes_tool_call() -> None:
    @define_agent
    def WeatherAgent() -> str:
        use_model("test/model")
        use_tool(local_weather)
        return "You are a weather assistant."

    provider = FakeProvider(
        tool_calls=[ToolCall(id="call-1", name="local_weather", arguments={"city": "Paris"})]
    )
    result = await run_agent(WeatherAgent, "weather in Paris", provider=provider)
    assert "Local weather in Paris" in result


@pytest.mark.anyio
async def test_run_agent_model_override() -> None:
    @define_agent
    def ModelAgent() -> str:
        use_model("test/old")
        return "instructions"

    provider = FakeProvider(reply="ok")
    await run_agent(ModelAgent, "hi", provider=provider, model="test/new")
    # The fake provider ignores model, but the call should succeed.


@pytest.mark.anyio
async def test_run_agent_max_turns_passed_to_harness() -> None:
    """run_agent should pass max_turns so the harness enforces a turn limit."""

    @define_agent
    def TurnAgent() -> str:
        use_model("test/model")
        return "instructions"

    provider = FakeProvider(reply="done")
    # Default max_turns is 25 — verify it doesn't interfere with a simple run.
    result = await run_agent(TurnAgent, "hi", provider=provider)
    assert result == "done"


@pytest.mark.anyio
async def test_run_agent_timeout_accepted() -> None:
    """timeout parameter is accepted and does not break a fast call."""

    @define_agent
    def FastAgent() -> str:
        use_model("test/model")
        return "instructions"

    result = await run_agent(FastAgent, "hi", provider=FakeProvider(reply="ok"), timeout=30)
    assert result == "ok"


class _CaptureSystemProvider(FakeProvider):
    """FakeProvider that records the system prompt it was given."""

    def stream_response(self, **kwargs: Any) -> AsyncIterator[AssistantMessageEvent]:
        self.system = kwargs["system"]
        return super().stream_response(**kwargs)


@pytest.mark.anyio
async def test_use_prompt_contents_reach_system_prompt(tmp_path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("file instructions")

    @define_agent
    def MyAgent() -> None:
        use_model("test/model")
        use_prompt(prompt_file)

    provider = _CaptureSystemProvider(reply="ok")
    result = await run_agent(MyAgent, "hi", provider=provider)
    assert result == "ok"
    assert "file instructions" in provider.system


class _TalkThenToolProvider(FakeProvider):
    """Streams prose in turn 1 before a tool call, then answers in turn 2."""

    def stream_response(
        self,
        *,
        model: str,
        system: str,
        messages: list[Any],
        tools: list[Any],
        signal: CancellationToken | None = None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        self._tool_turn_done = not self._tool_turn_done
        if self._tool_turn_done:
            # Turn 1: stream prose, then request a tool call.
            async def first() -> AsyncIterator[AssistantMessageEvent]:
                partial = AssistantMessage(content=[TextContent(text="Let me check")])
                yield AssistantStartEvent(partial=partial)
                yield TextDeltaEvent(content_index=0, delta="Let me check", partial=partial)
                done = AssistantMessage(
                    content=[
                        TextContent(text="Let me check"),
                        ToolCall(id="call-1", name="local_weather", arguments={"city": "Paris"}),
                    ]
                )
                yield AssistantDoneEvent(reason="toolUse", message=done)

            return first()

        # Turn 2: final answer.
        async def second() -> AsyncIterator[AssistantMessageEvent]:
            partial = AssistantMessage(content=[TextContent(text="It's 22C.")])
            yield AssistantStartEvent(partial=partial)
            yield TextDeltaEvent(content_index=0, delta="It's 22C.", partial=partial)
            yield AssistantDoneEvent(
                reason="stop",
                message=AssistantMessage(content=[TextContent(text="It's 22C.")]),
            )

        return second()


@pytest.mark.anyio
async def test_run_agent_returns_only_final_message_text() -> None:
    """Intermediate turn prose must not leak into the returned text."""

    @define_agent
    def Agent() -> str:
        use_model("test/model")
        use_tool(local_weather)
        return ""

    result = await run_agent(Agent, "hi", provider=_TalkThenToolProvider(reply=""))
    assert result == "It's 22C."


class _EmptyFinalProvider(FakeProvider):
    """Streams prose in turn 1 before a tool call, then ends with no text."""

    def stream_response(
        self,
        *,
        model: str,
        system: str,
        messages: list[Any],
        tools: list[Any],
        signal: CancellationToken | None = None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        self._tool_turn_done = not self._tool_turn_done
        if self._tool_turn_done:
            # Turn 1: stream prose, then request a tool call.
            async def first() -> AsyncIterator[AssistantMessageEvent]:
                partial = AssistantMessage(content=[TextContent(text="Let me check")])
                yield AssistantStartEvent(partial=partial)
                yield TextDeltaEvent(content_index=0, delta="Let me check", partial=partial)
                done = AssistantMessage(
                    content=[
                        TextContent(text="Let me check"),
                        ToolCall(id="call-1", name="local_weather", arguments={"city": "Paris"}),
                    ]
                )
                yield AssistantDoneEvent(reason="toolUse", message=done)

            return first()

        # Turn 2: final answer with NO text content.
        async def second() -> AsyncIterator[AssistantMessageEvent]:
            partial = AssistantMessage(content=[])
            yield AssistantStartEvent(partial=partial)
            yield AssistantDoneEvent(reason="stop", message=AssistantMessage(content=[]))

        return second()


@pytest.mark.anyio
async def test_run_agent_empty_final_message_returns_empty_string() -> None:
    """An empty final message must not leak intermediate turn prose."""

    @define_agent
    def Agent() -> str:
        use_model("test/model")
        use_tool(local_weather)
        return ""

    result = await run_agent(Agent, "hi", provider=_EmptyFinalProvider(reply=""))
    assert result == ""


class _RaisingProvider(FakeProvider):
    """Provider whose transport raises mid-stream."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.aclose_called = False

    async def aclose(self) -> None:
        self.aclose_called = True

    def stream_response(self, **kwargs: Any) -> AsyncIterator[AssistantMessageEvent]:
        async def boom() -> AsyncIterator[AssistantMessageEvent]:
            raise ConnectionError("upstream refused")
            yield  # unreachable; makes this an async generator

        return boom()


@pytest.mark.anyio
async def test_run_agent_wraps_transport_errors(caplog: pytest.LogCaptureFixture) -> None:
    @define_agent
    def Agent() -> str:
        use_model("test/model")
        return ""

    with pytest.raises(RuntimeError, match=r"Provider error \(ConnectionError\): upstream refused"):
        await run_agent(Agent, "hi", provider=_RaisingProvider(reply=""))
    assert "run_agent failed" in caplog.text


class _SlowProvider(FakeProvider):
    """Provider that sleeps longer than any test timeout."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.aclose_called = False

    async def aclose(self) -> None:
        self.aclose_called = True

    def stream_response(self, **kwargs: Any) -> AsyncIterator[AssistantMessageEvent]:
        async def slow() -> AsyncIterator[AssistantMessageEvent]:
            await asyncio.sleep(5)
            yield AssistantStartEvent(partial=AssistantMessage(content=[TextContent(text="never")]))

        return slow()


@pytest.mark.anyio
async def test_run_agent_timeout_fires() -> None:
    """A slow provider must be cut off by the timeout, re-raised as-is."""

    @define_agent
    def Agent() -> str:
        use_model("test/model")
        return ""

    provider = _SlowProvider(reply="")
    with pytest.raises(TimeoutError):
        await run_agent(Agent, "hi", provider=provider, timeout=0.1)
    # An injected provider is caller-owned; run_agent must not close it.
    assert provider.aclose_called is False


@pytest.mark.anyio
async def test_run_agent_closes_provider_on_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider created by run_agent must be closed even when the run fails."""

    @define_agent
    def Agent() -> str:
        use_model("test/model")
        return ""

    provider = _RaisingProvider(reply="")
    monkeypatch.setattr("tauon.agent.default_provider", lambda **kwargs: provider)

    with pytest.raises(RuntimeError, match="upstream refused"):
        await run_agent(Agent, "hi")
    assert provider.aclose_called is True


class _AlwaysToolProvider(FakeProvider):
    """Requests a tool call on every turn (runaway tool loop)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.call_count = 0

    def stream_response(
        self,
        *,
        model: str,
        system: str,
        messages: list[Any],
        tools: list[Any],
        signal: CancellationToken | None = None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        self.call_count += 1

        async def loop() -> AsyncIterator[AssistantMessageEvent]:
            message = AssistantMessage(
                content=[
                    TextContent(text=""),
                    ToolCall(id="call-1", name="local_weather", arguments={"city": "Paris"}),
                ]
            )
            yield AssistantStartEvent(partial=message)
            yield AssistantDoneEvent(reason="toolUse", message=message)

        return loop()


@pytest.mark.anyio
async def test_run_agent_stops_at_max_turns() -> None:
    """A runaway tool loop must stop once max_turns is reached."""

    @define_agent
    def Agent() -> str:
        use_model("test/model")
        use_tool(local_weather)
        return ""

    provider = _AlwaysToolProvider(reply="")
    with pytest.raises(RuntimeError, match=r"Agent stopped after max_turns=2"):
        await run_agent(Agent, "hi", provider=provider, max_turns=2)
    # The tool loop actually ran before the limit stopped it.
    assert provider.call_count == 2


@pytest.mark.anyio
async def test_run_agent_raises_on_max_turns_stop() -> None:
    @define_agent
    def Agent() -> str:
        use_model("test/model")
        return ""

    with pytest.raises(RuntimeError, match="max_turns must be at least 1"):
        await run_agent(Agent, "hi", provider=FakeProvider(reply="x"), max_turns=0)
