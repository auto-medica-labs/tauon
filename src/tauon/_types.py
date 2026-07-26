"""Internal shared types for Tauon."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from tau_agent.tools import AgentTool
from tau_agent.types import JSONValue

type ToolLike = AgentTool


@runtime_checkable
class Agent(Protocol):
    """A decorated agent function."""

    def __call__(self) -> str | None: ...

    _tauon_agent: Literal[True]


class AgentFn(Protocol):
    """A plain agent function before decoration."""

    def __call__(self) -> str | None: ...

    __name__: str


__all__ = ["Agent", "AgentFn", "JSONValue", "ToolLike"]
