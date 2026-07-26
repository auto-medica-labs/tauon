"""Tests for tool definition and execution."""

from __future__ import annotations

from typing import cast

import pytest

from tauon import define_tool
from tauon.tool import AgentTool


@define_tool
def sync_tool(name: str, count: int) -> str:
    """A sync tool."""
    return f"{name}: {count}"


@define_tool
async def async_tool(name: str) -> str:
    """An async tool."""
    return f"async {name}"


@define_tool
def no_doc(name: str) -> str:
    return f"hello {name}"


def test_define_tool_returns_agent_tool() -> None:
    assert isinstance(sync_tool, AgentTool)


def test_tool_schema_includes_parameters() -> None:
    from typing import Any

    schema = sync_tool.parameters
    properties = cast(dict[str, Any], schema["properties"])
    required = cast(list[str], schema["required"])
    assert schema["type"] == "object"
    assert "name" in properties
    assert "count" in properties
    assert "name" in required
    assert "count" in required


@pytest.mark.anyio
async def test_sync_tool_execution() -> None:
    result = await sync_tool.execute("call-1", {"name": "foo", "count": 3})
    assert result.text == "foo: 3"


@pytest.mark.anyio
async def test_async_tool_execution() -> None:
    result = await async_tool.execute("call-1", {"name": "foo"})
    assert result.text == "async foo"


def test_tool_description_from_docstring() -> None:
    assert sync_tool.description == "A sync tool."


def test_tool_without_docstring_has_empty_description() -> None:
    assert no_doc.description == ""
