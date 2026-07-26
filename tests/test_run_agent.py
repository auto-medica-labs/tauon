"""Tests for running agents with a fake provider."""

from __future__ import annotations

import pytest
from tau_agent.messages import ToolCall

from conftest import FakeProvider
from tauon import define_agent, define_tool, use_model, use_tool
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
