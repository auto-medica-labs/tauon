"""Tool definition and schema generation."""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable, Mapping
from typing import Any, Protocol, cast

from pydantic import create_model
from tau_agent.messages import TextContent
from tau_agent.tools import AgentTool, AgentToolResult
from tau_agent.types import JSONValue


class _ToolFn(Protocol):
    """Function shape accepted by define_tool."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

    __name__: str
    __doc__: str | None


def _extract_doc_parts(doc: str | None) -> tuple[str, str | None]:
    """Return (description, prompt_snippet) from a docstring.

    The first paragraph becomes the description; an optional second paragraph,
    separated by a blank line, becomes the prompt_snippet.
    """
    if not doc:
        return "", None
    paragraphs = [p.strip() for p in doc.strip().split("\n\n") if p.strip()]
    if not paragraphs:
        return "", None
    description = " ".join(paragraphs[0].split())
    prompt_snippet = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else None
    return description, prompt_snippet


def define_tool[F: Callable[..., Any]](fn: F) -> AgentTool:
    """Turn a typed Python function into an agent tool."""
    tool_fn = cast(_ToolFn, fn)
    sig = inspect.signature(tool_fn)

    # Reject *args and **kwargs — not representable as JSON schema params.
    for _name, param in sig.parameters.items():
        if param.kind is inspect.Parameter.VAR_POSITIONAL:
            msg = f"Tool function {tool_fn.__name__!r} must not use *args"
            raise TypeError(msg)
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            msg = f"Tool function {tool_fn.__name__!r} must not use **kwargs"
            raise TypeError(msg)

    # Resolve postponed (string) annotations so Pydantic gets real types.
    try:
        hints = typing.get_type_hints(tool_fn)
    except Exception:
        hints = {}

    fields: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        annotation = hints.get(name, param.annotation)
        if annotation is inspect.Parameter.empty:
            annotation = Any
        default = param.default if param.default is not inspect.Parameter.empty else ...
        fields[name] = (annotation, default)

    model_name = f"{tool_fn.__name__}_args"
    arg_model = create_model(model_name, **fields)
    schema = arg_model.model_json_schema()

    description, prompt_snippet = _extract_doc_parts(tool_fn.__doc__)

    async def execute_fn(
        tool_call_id: str,
        arguments: Mapping[str, JSONValue],
        signal: Any = None,
        on_update: Any = None,
    ) -> AgentToolResult:
        validated = arg_model.model_validate(dict(arguments))
        kwargs = validated.model_dump()
        if inspect.iscoroutinefunction(tool_fn):
            result = await tool_fn(**kwargs)
        else:
            result = tool_fn(**kwargs)
        return AgentToolResult(content=[TextContent(text=str(result))])

    return AgentTool(
        name=tool_fn.__name__,
        label=tool_fn.__name__,
        description=description,
        parameters=schema,
        execute_fn=execute_fn,  # type: ignore[arg-type]
        prompt_snippet=prompt_snippet,
    )


__all__ = ["AgentTool", "define_tool"]
