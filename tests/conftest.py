"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from tau_agent.messages import (
    AssistantMessage,
    TextContent,
    ToolCall,
    ToolResultMessage,
)
from tau_agent.provider import CancellationToken, ModelProvider
from tau_agent.provider_events import (
    AssistantDoneEvent,
    AssistantStartEvent,
    TextDeltaEvent,
)
from tau_ai.events import AssistantMessageEvent

from tauon import define_tool
from tauon.agent import run_agent


@define_tool
def fake_weather(city: str) -> str:
    """Get the fake weather for a city."""
    return f"Fake sunny 25°C in {city}."


class FakeProvider(ModelProvider):
    """A fake provider that echoes or calls tools for tests."""

    def __init__(self, reply: str | None = None, tool_calls: list[ToolCall] | None = None) -> None:
        self.reply = reply or ""
        self.tool_calls = tool_calls or []
        self._tool_turn_done = False

    async def aclose(self) -> None:
        return

    def stream_response(
        self,
        *,
        model: str,
        system: str,
        messages: list[Any],
        tools: list[Any],
        signal: CancellationToken | None = None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        async def iterator() -> AsyncIterator[AssistantMessageEvent]:
            if self.tool_calls and not self._tool_turn_done:
                content: list[Any] = [TextContent(text=""), *self.tool_calls]
                message = AssistantMessage(content=content)
                yield AssistantStartEvent(partial=message)
                yield AssistantDoneEvent(reason="toolUse", message=message)
                self._tool_turn_done = True
                return

            # After a tool call, echo the most recent tool result back so tests
            # can observe the full tool-call path in the final assistant text.
            last_tool_text = ""
            for message in reversed(messages):
                if isinstance(message, ToolResultMessage):
                    last_tool_text = message.text
                    break

            reply = self.reply or last_tool_text
            content = [TextContent(text="")]
            message = AssistantMessage(content=content)
            yield AssistantStartEvent(partial=message)
            for chunk in reply:
                yield TextDeltaEvent(
                    content_index=0,
                    delta=chunk,
                    partial=AssistantMessage(content=[TextContent(text=chunk)]),
                )
            yield AssistantDoneEvent(
                reason="stop",
                message=AssistantMessage(content=[TextContent(text=reply)]),
            )

        return iterator()


__all__ = ["FakeProvider", "fake_weather", "run_agent"]
