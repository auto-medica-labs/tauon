"""Tests for agent definition and frame collection."""

from __future__ import annotations

from typing import cast

import pytest

from tauon import define_agent, define_tool, use_model, use_tool
from tauon._types import AgentFn
from tauon.agent import define_agent as define_agent_raw
from tauon.hooks import collect_frame
from tauon.hooks import use_model as use_model_raw
from tauon.hooks import use_tool as use_tool_raw


@define_tool
def dummy_tool(name: str) -> str:
    """A dummy tool."""
    return f"hello {name}"


def test_define_agent_tags_function() -> None:
    @define_agent
    def MyAgent() -> str:
        use_model("test/model")
        return "instructions"

    assert getattr(MyAgent, "_tauon_agent", False) is True


def test_define_agent_rejects_required_arguments() -> None:
    def _bad(required: str) -> str:
        return ""

    with pytest.raises(TypeError, match="must not have required parameters"):
        define_agent_raw(cast(AgentFn, _bad))


def test_define_agent_rejects_async_functions() -> None:
    async def _async_agent() -> str:
        return ""

    with pytest.raises(TypeError, match="plain \(sync\) function"):
        define_agent_raw(cast(AgentFn, _async_agent))


def test_hooks_outside_agent_raise() -> None:
    with pytest.raises(RuntimeError, match="use_model"):
        use_model_raw("test/model")
    with pytest.raises(RuntimeError, match="use_tool"):
        use_tool_raw(dummy_tool)


def test_collect_frame_gathers_model_tools_and_instructions() -> None:
    @define_agent
    def MyAgent() -> str:
        use_model("test/model")
        use_tool(dummy_tool)
        return "Do things."

    frame = collect_frame(MyAgent)
    assert frame.model == "test/model"
    assert len(frame.tools) == 1
    assert frame.tools[0].name == "dummy_tool"
    assert frame.instructions == "Do things."


def test_collect_frame_requires_model() -> None:
    @define_agent
    def MyAgent() -> str:
        return "Do things."

    frame = collect_frame(MyAgent)
    assert frame.model is None


def test_duplicate_tool_raises() -> None:
    @define_tool
    def dup_tool(x: str) -> str:
        """Dup."""
        return x

    @define_agent
    def BadAgent() -> str:
        use_model("test/model")
        use_tool(dup_tool)
        use_tool(dup_tool)  # same object, same name
        return ""

    with pytest.raises(RuntimeError, match="Duplicate tool.*dup_tool"):
        collect_frame(BadAgent)
