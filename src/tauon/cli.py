"""Command-line interface for Tauon."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

import anyio
import typer

from tauon._types import Agent
from tauon.agent import run_agent

app = typer.Typer(help="Tauon agent runner")


@app.callback()
def _main() -> None:
    """Tauon agent runner."""


def _load_agent_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        msg = f"Could not load module from {path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    # Make sibling imports work: the script's directory must be importable.
    parent = str(path.parent)
    sys.path.insert(0, parent)
    try:
        spec.loader.exec_module(module)
    finally:
        with suppress(ValueError):
            sys.path.remove(parent)
    return module


def _find_agent(module: Any) -> Agent:
    agents = [
        obj
        for _name, obj in inspect.getmembers(module)
        if callable(obj) and getattr(obj, "_tauon_agent", False)
    ]
    if not agents:
        msg = f"No agent found in {module.__file__}"
        raise RuntimeError(msg)
    if len(agents) > 1:
        names = ", ".join(agent.__name__ for agent in agents)
        msg = (
            f"Multiple agents found in {module.__file__}: {names}. "
            "Keep exactly one agent per module."
        )
        raise RuntimeError(msg)
    return agents[0]  # type: ignore[return-value]


@app.command()
def run(
    path: Path,
    message: str = typer.Option(..., "--message", "-m", help="User message to send"),
    model: str | None = typer.Option(None, "--model", help="Override the agent model"),
    provider: str | None = typer.Option(
        None, "--provider", help="Override the provider (e.g. openai, anthropic)"
    ),
) -> None:
    """Load an agent module and run it with MESSAGE."""
    module = _load_agent_module(path)
    agent = _find_agent(module)
    # Keep the script's directory importable for the whole run, matching
    # `python script.py` semantics — agent bodies and tools may import
    # siblings lazily at run time, not just at load time.
    parent = str(path.parent)
    sys.path.insert(0, parent)
    try:
        reply = anyio.run(lambda: run_agent(agent, message, model=model, provider_name=provider))
    finally:
        with suppress(ValueError):
            sys.path.remove(parent)
    typer.echo(reply)


if __name__ == "__main__":
    app()


__all__ = ["app"]
