"""Default provider factory using Tau's built-in provider catalog."""

from __future__ import annotations

from os import environ

from tau_agent.provider import ModelProvider
from tau_ai.env import DEFAULT_OPENAI_COMPATIBLE_BASE_URL, OpenAICompatibleConfig
from tau_ai.openai_compatible import OpenAICompatibleProvider
from tau_coding.provider_config import (
    ProviderConfigError,
    load_provider_settings,
    resolve_provider_selection,
)
from tau_coding.provider_runtime import create_model_provider


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

    Resolves the provider and model the same way Tau does, so any model usable
    in Tau is usable in Tauon without manual endpoint or reasoning-effort
    configuration. ``OPENAI_API_KEY``/``ANTHROPIC_API_KEY``/etc. are read from
    the environment by the catalog runtime.

    Explicit ``base_url`` or ``api_key`` fall back to a plain
    OpenAI-compatible provider when the model is not in Tau's catalog.
    """
    has_override = api_key is not None or base_url is not None

    if model and not has_override:
        settings = load_provider_settings()
        target_provider = provider_name
        target_model = model

        if provider_name is None and "/" in model:
            target_provider, _, target_model = model.partition("/")
            target_provider = target_provider.strip() or None
            target_model = target_model.strip() or None

        if target_provider is not None and target_model is not None:
            try:
                selection = resolve_provider_selection(
                    settings,
                    provider_name=target_provider,
                    model=target_model,
                )
                return create_model_provider(
                    selection.provider,
                    model=selection.model,
                )
            except ProviderConfigError:
                if provider_name is not None:
                    raise
                # Fall through to default-provider resolution below.

        if target_model is not None:
            try:
                selection = resolve_provider_selection(
                    settings,
                    model=target_model,
                )
                return create_model_provider(
                    selection.provider,
                    model=selection.model,
                )
            except ProviderConfigError:
                pass

    return _simple_openai_provider(api_key=api_key, base_url=base_url)


__all__ = ["default_provider"]
