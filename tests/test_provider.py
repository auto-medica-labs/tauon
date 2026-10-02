"""Tests for provider resolution hermeticity from ``$TAU_HOME``."""

from __future__ import annotations

from pathlib import Path

import pytest

from tauon.provider import default_provider

_CANARIES = {
    "providers.json": "{this is not json",
    "credentials.json": "{this is not json",
    "catalog.toml": "not = valid = toml [",
    "models-store.json": "{this is not json",
    "codex-version-store.json": "{this is not json",
}


def _write_canaries(home: Path) -> dict[str, str]:
    """Write deliberately invalid state files and return their original contents.

    Any attempt to parse one raises, and any write changes its contents, so a
    single assertion covers both reads and writes.
    """
    for name, content in _CANARIES.items():
        (home / name).write_text(content, encoding="utf-8")
    return {name: (home / name).read_text(encoding="utf-8") for name in _CANARIES}


def _assert_canaries_untouched(home: Path, before: dict[str, str]) -> None:
    for name, content in before.items():
        assert (home / name).read_text(encoding="utf-8") == content


def test_catalog_resolution_does_not_touch_tau_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolving bundled catalog providers must never read or write $TAU_HOME."""
    monkeypatch.setenv("TAU_HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    before = _write_canaries(tmp_path)

    # Would raise if providers.json/catalog.toml/credentials.json were parsed.
    assert default_provider(model="openai/gpt-5.4") is not None
    assert default_provider(model="anthropic/claude-sonnet-4-6") is not None

    _assert_canaries_untouched(tmp_path, before)


def test_explicit_endpoint_override_does_not_touch_tau_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """api_key/base_url overrides must not fall back to $TAU_HOME state."""
    monkeypatch.setenv("TAU_HOME", str(tmp_path))
    before = _write_canaries(tmp_path)

    provider = default_provider(
        model="custom-model",
        api_key="test-key",
        base_url="https://example.test/v1",
    )

    assert provider is not None
    _assert_canaries_untouched(tmp_path, before)


def test_bare_model_requires_provider_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """A model without provider/model syntax must be rejected."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    with pytest.raises(RuntimeError, match="must be prefixed with a provider"):
        default_provider(model="gpt-4.1-mini")


def test_bare_model_allowed_with_explicit_provider_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit provider_name makes a bare model unambiguous."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    assert default_provider(model="gpt-5.4", provider_name="openai") is not None
