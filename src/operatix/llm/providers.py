"""Provider-neutral chat model construction."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

from langchain_core.language_models.chat_models import BaseChatModel


class Provider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    label: str
    key_env: str
    model_env: str
    default_model: str
    credentials_url: str
    auth_hint: str


PROVIDER_SPECS: dict[Provider, ProviderSpec] = {
    Provider.OPENAI: ProviderSpec(
        label="OpenAI",
        key_env="OPENAI_API_KEY",
        model_env="OPENAI_MODEL",
        default_model="gpt-5.4-mini",
        credentials_url="https://platform.openai.com/api-keys",
        auth_hint="Clave de proyecto de OpenAI Platform.",
    ),
    Provider.ANTHROPIC: ProviderSpec(
        label="Anthropic",
        key_env="ANTHROPIC_API_KEY",
        model_env="ANTHROPIC_MODEL",
        default_model="claude-sonnet-4-6",
        credentials_url="https://console.anthropic.com/settings/keys",
        auth_hint="Clave de API de Anthropic Console.",
    ),
    Provider.GOOGLE: ProviderSpec(
        label="Google Gemini",
        key_env="GOOGLE_API_KEY",
        model_env="GOOGLE_MODEL",
        default_model="gemini-2.5-flash",
        credentials_url="https://aistudio.google.com/app/apikey",
        auth_hint="Clave de Google AI Studio para Gemini.",
    ),
}


class ProviderConfigurationError(ValueError):
    """Raised when a selected provider has incomplete configuration."""


def friendly_provider_error(error: Exception) -> str:
    """Translate common cloud-provider failures into safe, actionable feedback."""
    raw_message = str(error)
    message = raw_message.lower()
    if "insufficient_quota" in message or "current quota" in message:
        return (
            "OpenAI no tiene cuota o crédito disponible para este proyecto. "
            "Revisa facturación en https://platform.openai.com/settings/organization/billing "
            "y los límites en https://platform.openai.com/settings/organization/limits."
        )
    if "rate_limit_exceeded" in message:
        return "El proveedor alcanzó un límite temporal. Espera unos segundos y vuelve a intentar."
    if "invalid_api_key" in message or "authentication" in message and "401" in message:
        return "La clave del proveedor no es válida o no pertenece al proyecto seleccionado."
    if isinstance(error, ProviderConfigurationError):
        return raw_message
    return f"El proveedor de IA devolvió un error: {raw_message}"


def provider_is_configured(provider: Provider | str) -> bool:
    resolved = Provider(provider)
    return bool(os.getenv(PROVIDER_SPECS[resolved].key_env, "").strip())


def resolve_model_name(provider: Provider | str, override: str | None = None) -> str:
    resolved = Provider(provider)
    spec = PROVIDER_SPECS[resolved]
    return (override or os.getenv(spec.model_env) or spec.default_model).strip()


def build_chat_model(
    provider: Provider | str,
    model_name: str | None = None,
    temporary_api_key: str | None = None,
) -> BaseChatModel:
    """Build one of the supported LangChain chat model integrations.

    A temporary key is passed directly to the SDK instance and is never written to disk.
    When it is absent, the provider-specific environment variable is used.
    """
    resolved = Provider(provider)
    spec = PROVIDER_SPECS[resolved]
    api_key = (temporary_api_key or os.getenv(spec.key_env) or "").strip()
    if not api_key:
        raise ProviderConfigurationError(
            f"Configura {spec.key_env} o introduce una clave temporal para {spec.label}."
        )

    model = resolve_model_name(resolved, model_name)
    if resolved is Provider.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=api_key, temperature=0)
    if resolved is Provider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, api_key=api_key, temperature=0, max_tokens=1024)

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=0)
