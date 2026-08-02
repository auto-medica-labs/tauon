"""Agent render frame and hooks used inside agent bodies."""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tau_agent.tools import AgentTool


@dataclass
class RenderFrame:
    """Collected configuration from one agent render."""

    model: str | None = None
    tools: list[AgentTool] = field(default_factory=list)
    instructions: str | None = None
    module_dir: Path | None = None
    # Directory of the module that defines the agent; used to resolve
    # relative ``use_prompt`` paths.


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
    for existing in frame.tools:
        if existing.name == tool.name:
            msg = f"Duplicate tool {tool.name!r} in agent render"
            raise RuntimeError(msg)
    frame.tools.append(tool)


def use_prompt(path: str | Path) -> None:
    """Load a system prompt from a text file (e.g. a markdown file).

    Relative paths resolve against the directory of the module that defines
    the agent, so ``use_prompt("prompt.md")`` works from any launch
    directory. Agents defined without a module file (REPL, ``-c``) fall back
    to resolving against the current working directory.
    """
    frame = _current_frame.get()
    if frame is None:
        msg = "use_prompt must be called inside an agent function decorated with @define_agent"
        raise RuntimeError(msg)
    if frame.instructions is not None:
        msg = "System prompt already set; use either use_prompt() or the return value, not both"
        raise RuntimeError(msg)
    prompt_path = Path(path)
    if not prompt_path.is_absolute() and frame.module_dir is not None:
        prompt_path = frame.module_dir / prompt_path
    frame.instructions = prompt_path.read_text(encoding="utf-8")


def collect_frame(agent_fn: Callable[[], str | None]) -> RenderFrame:  # type: ignore[name-defined]
    """Run ``agent_fn`` inside a fresh render frame and return it."""
    frame = RenderFrame()
    module_file = agent_fn.__globals__.get("__file__")  # type: ignore[attr-defined]
    if module_file:
        frame.module_dir = Path(module_file).resolve().parent
    token = _current_frame.set(frame)
    try:
        returned = agent_fn()
    finally:
        _current_frame.reset(token)
    if returned is not None:
        if frame.instructions is not None:
            msg = (
                "System prompt set both by use_prompt() and by the agent return "
                "value; use one or the other"
            )
            raise RuntimeError(msg)
        frame.instructions = returned
    return frame


__all__ = ["RenderFrame", "collect_frame", "use_model", "use_prompt", "use_tool"]
