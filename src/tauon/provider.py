"""Default provider factory using Tau's built-in provider catalog."""

from __future__ import annotations

import logging
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

logger = logging.getLogger("tauon")


def _split_model_spec(model: str) -> tuple[str | None, str]:
    """Return (provider_name, bare_model) from a model specifier.

    Supports ``provider/model`` syntax; bare model names are returned as-is.
    """
    if "/" in model:
        provider_part, _, model_part = model.partition("/")
        provider_part = provider_part.strip()
        model_part = model_part.strip()
        if provider_part and model_part:
            return provider_part, model_part
    return None, model


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
    # Treat empty-string overrides as unset: "" is not a real api_key/base_url.
    api_key = api_key or None
    base_url = base_url or None
    has_override = api_key is not None or base_url is not None

    if model and not has_override:
        settings = ProviderSettings()
        if provider_name is None:
            provider_name, model = _split_model_spec(model)

        if provider_name is not None:
            # Explicit provider names fail loudly; no silent fallback. Wrap
            # tau-internal config errors so callers see one error contract.
            try:
                return _try_create_provider(
                    settings,
                    provider_name=provider_name,
                    model=model,
                )
            except ProviderConfigError as exc:
                msg = f"Provider config error: {exc}"
                raise RuntimeError(msg) from exc

        try:
            return _try_create_provider(settings, model=model)
        except ProviderConfigError:
            logger.warning(
                "Model %r is not in Tau's provider catalog; falling back to a "
                "plain OpenAI-compatible provider (needs OPENAI_API_KEY). "
                "Use 'provider/model' to force a specific provider.",
                model,
            )

    return _simple_openai_provider(api_key=api_key, base_url=base_url)


__all__ = ["default_provider"]
