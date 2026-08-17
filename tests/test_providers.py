import pytest

from operatix.llm.providers import (
    PROVIDER_SPECS,
    Provider,
    ProviderConfigurationError,
    build_chat_model,
    friendly_provider_error,
    provider_is_configured,
    resolve_model_name,
)


def test_provider_status_and_model_can_be_configured(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "custom-model")

    assert provider_is_configured(Provider.ANTHROPIC) is True
    assert resolve_model_name(Provider.ANTHROPIC) == "custom-model"
    assert PROVIDER_SPECS[Provider.ANTHROPIC].key_env == "ANTHROPIC_API_KEY"


def test_missing_provider_key_gives_actionable_error(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ProviderConfigurationError, match="GOOGLE_API_KEY"):
        build_chat_model(Provider.GOOGLE)


def test_quota_error_is_not_reported_as_transient_rate_limit() -> None:
    error = RuntimeError("429 insufficient_quota: You exceeded your current quota")

    message = friendly_provider_error(error)

    assert "cuota o crédito" in message
    assert "billing" in message
