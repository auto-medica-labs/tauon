"""Internal shared types for Tauon."""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from tau_agent.types import JSONValue


@runtime_checkable
class Agent(Protocol):
    """A decorated agent function."""

    def __call__(self) -> str | None: ...

    __name__: str

    @property
    def __globals__(self) -> dict[str, Any]: ...

    _tauon_agent: Literal[True]


class AgentFn(Protocol):
    """A plain agent function before decoration."""

    def __call__(self) -> str | None: ...

    __name__: str

    @property
    def __globals__(self) -> dict[str, Any]: ...


__all__ = ["Agent", "AgentFn", "JSONValue"]
