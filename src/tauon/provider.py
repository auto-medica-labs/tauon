"""Default provider factory using Tau's built-in provider catalog."""

from __future__ import annotations

from os import environ
from typing import Any

from tau_agent.provider import ModelProvider
from tau_ai.env import DEFAULT_OPENAI_COMPATIBLE_BASE_URL, OpenAICompatibleConfig
from tau_ai.openai_compatible import OpenAICompatibleProvider
from tau_coding.credentials import FileCredentialStore
from tau_coding.provider_config import (
    ProviderConfigError,
    ProviderSettings,
    resolve_provider_selection,
)
from tau_coding.provider_runtime import create_model_provider


class _NoOpCredentialStore(FileCredentialStore):
    """Credential store that never returns saved credentials."""

    def _load(self) -> dict[str, Any]:
        return {}


_NO_OP_STORE = _NoOpCredentialStore()


def _try_create_provider(settings, **kwargs) -> ModelProvider:
    """Resolve and instantiate a model provider from Tau's catalog."""
    selection = resolve_provider_selection(settings, **kwargs)
    return create_model_provider(
        selection.provider,
        model=selection.model,
        credential_store=_NO_OP_STORE,
    )


def _simple_openai_provider(
    *,
    api_key: str | None,
    base_url: str | None,
) -> ModelProvider:
    """Fallback OpenAI-compatible provider for explicit overrides."""
    key = api_key or environ.get("OPENAI_API_KEY")
    if not key:
        msg = "Missing OpenAI API key. Set OPENAI_API_KEY or pass api_key=."
        raise RuntimeError(msg)
    config = OpenAICompatibleConfig(
        api_key=key,
        base_url=base_url or DEFAULT_OPENAI_COMPATIBLE_BASE_URL,
    )
    return OpenAICompatibleProvider(config)


def default_provider(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    provider_name: str | None = None,
) -> ModelProvider:
    """Create a provider using Tau's built-in catalog.

    Resolves the provider and model from Tau's built-in provider catalog.
    API keys are read from environment variables only; saved Tau credentials
    (``~/.tau/credentials.json``) and provider preferences
    (``~/.tau/providers.json``) are ignored.

    ``OPENAI_API_KEY``/``ANTHROPIC_API_KEY``/``OPENAI_CODEX_ACCESS_TOKEN``/etc.
    are read from the environment by the catalog runtime.

    Explicit ``base_url`` or ``api_key`` fall back to a plain
    OpenAI-compatible provider when the model is not in Tau's catalog.
    """
    has_override = api_key is not None or base_url is not None

    if model and not has_override:
        settings = ProviderSettings()
        target_provider = provider_name
        target_model = model

        if provider_name is None and "/" in model:
            target_provider, _, target_model = model.partition("/")
            target_provider = target_provider.strip() or None
            target_model = target_model.strip() or None

        if target_provider is not None and target_model is not None:
            try:
                return _try_create_provider(
                    settings,
                    provider_name=target_provider,
                    model=target_model,
                )
            except ProviderConfigError:
                if provider_name is not None:
                    raise
                # Fall through to default-provider resolution below.

        if target_model is not None:
            try:
                return _try_create_provider(
                    settings,
                    model=target_model,
                )
            except ProviderConfigError:
                pass

    return _simple_openai_provider(api_key=api_key, base_url=base_url)


__all__ = ["default_provider"]
