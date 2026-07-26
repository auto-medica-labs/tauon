"""Agent render frame and hooks used inside agent bodies."""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tau_agent.tools import AgentTool


@dataclass
class RenderFrame:
    """Collected configuration from one agent render."""

    model: str | None = None
    tools: list[AgentTool] = field(default_factory=list)
    instructions: str | None = None


_current_frame: ContextVar[RenderFrame | None] = ContextVar("tauon_frame", default=None)


def use_model(model: str) -> None:
    """Set the model used by the current agent render."""
    frame = _current_frame.get()
    if frame is None:
        msg = "use_model must be called inside an agent function decorated with @define_agent"
        raise RuntimeError(msg)
    frame.model = model


def use_tool(tool: AgentTool) -> None:
    """Register a tool with the current agent render."""
    frame = _current_frame.get()
    if frame is None:
        msg = "use_tool must be called inside an agent function decorated with @define_agent"
        raise RuntimeError(msg)
    frame.tools.append(tool)


def collect_frame(agent_fn: Callable[[], str | None]) -> RenderFrame:  # type: ignore[name-defined]
    """Run ``agent_fn`` inside a fresh render frame and return it."""
    frame = RenderFrame()
    token = _current_frame.set(frame)
    try:
        instructions = agent_fn()
    finally:
        _current_frame.reset(token)
    frame.instructions = instructions
    return frame


__all__ = ["RenderFrame", "collect_frame", "use_model", "use_tool"]
