"""Command-line interface for Tauon."""

from __future__ import annotations

import importlib.util
import inspect
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
    spec.loader.exec_module(module)
    return module


def _find_agent(module: Any) -> Agent:
    for _name, obj in inspect.getmembers(module):
        if callable(obj) and getattr(obj, "_tauon_agent", False):
            return obj  # type: ignore[return-value]
    msg = f"No agent found in {module.__file__}"
    raise RuntimeError(msg)


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
    reply = anyio.run(lambda: run_agent(agent, message, model=model, provider_name=provider))
    typer.echo(reply)


__all__ = ["app"]
