"""Minimal system prompt builder."""

from __future__ import annotations

from tauon.hooks import RenderFrame


def build_system_prompt(frame: RenderFrame) -> str:
    """Build a system prompt from the agent's instructions and tools."""
    parts: list[str] = []
    if frame.instructions:
        parts.append("<instructions>")
        parts.append(frame.instructions)
        parts.append("</instructions>")
    if frame.tools:
        parts.append("")
        parts.append("<tools>")
        for tool in frame.tools:
            snippet = f"{tool.description}"
            if tool.prompt_snippet:
                snippet += f"\n\n{tool.prompt_snippet}"
            parts.append(f"- {tool.name}: {snippet}")
        parts.append("</tools>")
    return "\n".join(parts)
