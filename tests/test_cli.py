"""Tests for the CLI module loader and agent discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from tauon.cli import _find_agent, _load_agent_module


def test_load_agent_module_with_sibling_import(tmp_path: Path) -> None:
    """Agent scripts may import sibling modules next to the script."""
    (tmp_path / "helper.py").write_text("VALUE = 42\n")
    script = tmp_path / "agent_script.py"
    script.write_text(
        "from helper import VALUE\n"
        "from tauon import define_agent, use_model\n"
        "\n"
        "@define_agent\n"
        "def MyAgent() -> str:\n"
        "    use_model('test/model')\n"
        "    return f'val={VALUE}'\n"
    )
    module = _load_agent_module(script)
    agent = _find_agent(module)
    assert agent.__name__ == "MyAgent"


def test_find_agent_rejects_multiple_agents(tmp_path: Path) -> None:
    script = tmp_path / "two_agents.py"
    script.write_text(
        "from tauon import define_agent, use_model\n"
        "\n"
        "@define_agent\n"
        "def AgentA() -> str:\n"
        "    use_model('test/model')\n"
        "    return 'a'\n"
        "\n"
        "@define_agent\n"
        "def AgentB() -> str:\n"
        "    use_model('test/model')\n"
        "    return 'b'\n"
    )
    module = _load_agent_module(script)
    with pytest.raises(RuntimeError, match="Multiple agents found.*AgentA.*AgentB"):
        _find_agent(module)


def test_find_agent_rejects_no_agent(tmp_path: Path) -> None:
    script = tmp_path / "no_agent.py"
    script.write_text("VALUE = 1\n")
    module = _load_agent_module(script)
    with pytest.raises(RuntimeError, match="No agent found"):
        _find_agent(module)
