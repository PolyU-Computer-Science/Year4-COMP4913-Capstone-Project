from __future__ import annotations

from typing import Any

import pytest
from crewai import LLM
from crewai.llms.providers.anthropic.completion import AnthropicCompletion
from crewai.llms.providers.gemini.completion import GeminiCompletion
from crewai.llms.providers.openai.completion import OpenAICompletion
from crewai.llms.providers.openai_compatible.completion import (
    OpenAICompatibleCompletion,
)

from email_assistant.service import (
    LLMConfigurationError,
    LLMProvider,
    LLMSettings,
    create_llm,
)


PROVIDER_ENVIRONMENTS: dict[str, dict[str, str]] = {
    "local": {
        "LLM_PROVIDER": "local",
        "LOCAL_MODEL": "qwen3:8b",
        "LOCAL_BASE_URL": "http://localhost:11434/v1",
    },
    "openai": {
        "LLM_PROVIDER": "openai",
        "OPENAI_MODEL": "gpt-4o-mini",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "OPENAI_API_KEY": "openai-test-secret",
    },
    "openrouter": {
        "LLM_PROVIDER": "openrouter",
        "OPENROUTER_MODEL": "openai/gpt-4o-mini",
        "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY": "openrouter-test-secret",
    },
    "anthropic": {
        "LLM_PROVIDER": "anthropic",
        "ANTHROPIC_MODEL": "claude-3-5-sonnet-20241022",
        "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
        "ANTHROPIC_API_KEY": "anthropic-test-secret",
    },
    "groq": {
        "LLM_PROVIDER": "groq",
        "GROQ_MODEL": "llama-3.3-70b-versatile",
        "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
        "GROQ_API_KEY": "groq-test-secret",
    },
    "deepseek": {
        "LLM_PROVIDER": "deepseek",
        "DEEPSEEK_MODEL": "deepseek-chat",
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEEPSEEK_API_KEY": "deepseek-test-secret",
    },
    "google": {
        "LLM_PROVIDER": "google",
        "GOOGLE_MODEL": "gemini-2.0-flash",
        "GOOGLE_API_KEY": "google-test-secret",
    },
}


@pytest.mark.parametrize(
    ("provider", "expected_model"),
    [
        ("local", "qwen3:8b"),
        ("openai", "gpt-4o-mini"),
        ("openrouter", "openai/gpt-4o-mini"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
        ("groq", "llama-3.3-70b-versatile"),
        ("deepseek", "deepseek-chat"),
        ("google", "gemini-2.0-flash"),
    ],
)
def test_from_env_reads_only_the_selected_provider(
    provider: str,
    expected_model: str,
) -> None:
    env = {
        **PROVIDER_ENVIRONMENTS[provider],
        "UNSELECTED_MODEL": "",
        "UNSELECTED_API_KEY": "",
    }

    settings = LLMSettings.from_env(env)

    assert settings.provider is LLMProvider(provider)
    assert settings.model == expected_model
    assert settings.temperature == 0.2
    assert settings.timeout == 120
    assert settings.max_tokens == 8000


def test_from_env_normalizes_provider_and_common_values() -> None:
    env = {
        **PROVIDER_ENVIRONMENTS["openai"],
        "LLM_PROVIDER": "  OPENAI  ",
        "LLM_TEMPERATURE": "0.7",
        "LLM_TIMEOUT": "45.5",
        "LLM_MAX_TOKENS": "4096",
    }

    settings = LLMSettings.from_env(env)

    assert settings.provider is LLMProvider.OPENAI
    assert settings.temperature == 0.7
    assert settings.timeout == 45.5
    assert settings.max_tokens == 4096


@pytest.mark.parametrize(
    ("env", "missing_name"),
    [
        ({}, "LLM_PROVIDER"),
        ({"LLM_PROVIDER": "unsupported"}, "LLM_PROVIDER"),
        ({"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "secret"}, "OPENAI_MODEL"),
        ({"LLM_PROVIDER": "openai", "OPENAI_MODEL": "gpt-4o-mini"}, "OPENAI_API_KEY"),
        ({"LLM_PROVIDER": "local", "LOCAL_MODEL": "qwen3:8b"}, "LOCAL_BASE_URL"),
    ],
)
def test_from_env_rejects_missing_or_unknown_selected_configuration(
    env: dict[str, str],
    missing_name: str,
) -> None:
    with pytest.raises(LLMConfigurationError, match=missing_name):
        LLMSettings.from_env(env)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("LLM_TEMPERATURE", "-0.1"),
        ("LLM_TEMPERATURE", "2.1"),
        ("LLM_TEMPERATURE", "warm"),
        ("LLM_TEMPERATURE", "nan"),
        ("LLM_TIMEOUT", "0"),
        ("LLM_TIMEOUT", "slow"),
        ("LLM_TIMEOUT", "inf"),
        ("LLM_MAX_TOKENS", "0"),
        ("LLM_MAX_TOKENS", "2.5"),
    ],
)
def test_from_env_rejects_invalid_common_values(name: str, value: str) -> None:
    env = {**PROVIDER_ENVIRONMENTS["local"], name: value}

    with pytest.raises(LLMConfigurationError, match=name):
        LLMSettings.from_env(env)


@pytest.mark.parametrize(
    "env",
    [
        {
            **PROVIDER_ENVIRONMENTS["local"],
            "LOCAL_BASE_URL": "localhost:11434/v1",
        },
        {
            **PROVIDER_ENVIRONMENTS["openai"],
            "OPENAI_BASE_URL": "not-a-url",
        },
    ],
)
def test_from_env_rejects_invalid_selected_base_url(env: dict[str, str]) -> None:
    with pytest.raises(LLMConfigurationError, match="BASE_URL"):
        LLMSettings.from_env(env)


def test_from_env_ignores_invalid_unselected_provider_values() -> None:
    env = {
        **PROVIDER_ENVIRONMENTS["openai"],
        "LOCAL_BASE_URL": "not-a-url",
        "ANTHROPIC_MODEL": "",
        "GOOGLE_API_KEY": "",
    }

    settings = LLMSettings.from_env(env)

    assert settings.provider is LLMProvider.OPENAI


def test_settings_repr_redacts_the_api_key() -> None:
    secret = "must-never-appear"

    settings = LLMSettings.from_env(
        {
            **PROVIDER_ENVIRONMENTS["openai"],
            "OPENAI_API_KEY": secret,
        }
    )

    assert secret not in repr(settings)


@pytest.mark.parametrize(
    ("provider", "expected_type", "expected_model"),
    [
        ("local", OpenAICompletion, "qwen3:8b"),
        ("openai", OpenAICompletion, "gpt-4o-mini"),
        ("openrouter", OpenAICompatibleCompletion, "openai/gpt-4o-mini"),
        ("anthropic", AnthropicCompletion, "claude-3-5-sonnet-20241022"),
        ("groq", LLM, "groq/llama-3.3-70b-versatile"),
        ("deepseek", OpenAICompatibleCompletion, "deepseek-chat"),
        ("google", GeminiCompletion, "gemini-2.0-flash"),
    ],
)
def test_create_llm_routes_each_provider_without_a_network_call(
    provider: str,
    expected_type: type[Any],
    expected_model: str,
) -> None:
    settings = LLMSettings.from_env(PROVIDER_ENVIRONMENTS[provider])

    llm = create_llm(settings)

    assert type(llm) is expected_type
    assert llm.model == expected_model
    assert llm.temperature == 0.2


def test_create_llm_maps_google_token_limit_to_max_output_tokens() -> None:
    settings = LLMSettings.from_env(
        {
            **PROVIDER_ENVIRONMENTS["google"],
            "LLM_MAX_TOKENS": "3210",
        }
    )

    llm = create_llm(settings)

    assert isinstance(llm, GeminiCompletion)
    assert llm.max_output_tokens == 3210
    assert llm.max_tokens is None


def test_create_llm_does_not_duplicate_an_existing_prefix() -> None:
    settings = LLMSettings.from_env(
        {
            **PROVIDER_ENVIRONMENTS["openai"],
            "OPENAI_MODEL": "openai/gpt-4o-mini",
        }
    )

    llm = create_llm(settings)

    assert type(llm) is OpenAICompletion
    assert llm.model == "gpt-4o-mini"


def test_configuration_errors_never_include_secret_values() -> None:
    secret = "secret-that-must-be-redacted"
    env = {
        **PROVIDER_ENVIRONMENTS["openai"],
        "OPENAI_API_KEY": secret,
        "LLM_TIMEOUT": "not-a-number",
    }

    with pytest.raises(LLMConfigurationError) as error:
        LLMSettings.from_env(env)

    assert secret not in str(error.value)


def test_local_api_key_is_optional_and_used_when_provided() -> None:
    env = {
        **PROVIDER_ENVIRONMENTS["local"],
        "LOCAL_API_KEY": "my-proxy-token",
    }

    settings = LLMSettings.from_env(env)

    assert settings.provider is LLMProvider.LOCAL
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "my-proxy-token"


def test_local_api_key_absent_is_still_valid() -> None:
    settings = LLMSettings.from_env(PROVIDER_ENVIRONMENTS["local"])

    assert settings.api_key is None


def test_from_generic_builds_settings_from_flat_dict() -> None:
    settings = LLMSettings.from_generic(
        {
            "provider": "local",
            "model": "qwen3:8b",
            "base_url": "http://localhost:11434/v1",
            "temperature": "0.7",
            "timeout": "45.5",
            "max_tokens": "4096",
        }
    )

    assert settings.provider is LLMProvider.LOCAL
    assert settings.model == "qwen3:8b"
    assert settings.temperature == 0.7
    assert settings.timeout == 45.5
    assert settings.max_tokens == 4096


def test_from_generic_rejects_missing_provider() -> None:
    with pytest.raises(LLMConfigurationError, match="provider"):
        LLMSettings.from_generic({"model": "qwen3:8b"})


def test_from_generic_rejects_provider_missing_api_key() -> None:
    with pytest.raises(LLMConfigurationError, match="api_key"):
        LLMSettings.from_generic(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "base_url": "https://api.openai.com/v1",
            }
        )
