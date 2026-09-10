"""LLM configuration and provider selection for the email assistant."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import math
import os
from typing import Any, Self
from urllib.parse import urlparse

from crewai import LLM
from crewai.llms.base_llm import BaseLLM
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class LLMProvider(StrEnum):
    """LLM providers supported by the application configuration."""

    LOCAL = "local"
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    GOOGLE = "google"


class LLMConfigurationError(ValueError):
    """Raised when the selected LLM provider is not configured correctly."""


class LLMSettings(BaseModel):
    """Validated, immutable configuration for one selected LLM provider."""

    model_config = ConfigDict(frozen=True)

    provider: LLMProvider
    model: str = Field(min_length=1)
    base_url: str | None = None
    api_key: SecretStr | None = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    timeout: float = Field(default=120, gt=0)
    max_tokens: int = Field(default=8000, gt=0)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Self:
        """Build settings from a mapping or the process environment.

        Only variables belonging to the selected provider are read and
        validated. When ``env`` is omitted, values from ``.env`` are loaded
        without overriding variables already present in the process.
        """

        if env is None:
            load_dotenv(override=False)
            source: Mapping[str, str] = os.environ
        else:
            source = env

        provider = _read_provider(source)
        spec = _PROVIDER_SPECS[provider]
        model = _required_value(source, spec.model_env)
        base_url = _optional_value(source, spec.base_url_env)
        api_key_value = _optional_value(source, spec.api_key_env)

        if spec.requires_base_url and base_url is None:
            raise LLMConfigurationError(f"{spec.base_url_env} is required")
        if base_url is not None:
            _validate_http_url(base_url, spec.base_url_env)

        if spec.requires_api_key and api_key_value is None:
            raise LLMConfigurationError(f"{spec.api_key_env} is required")

        temperature = _read_float(
            source,
            "LLM_TEMPERATURE",
            default=0.2,
            minimum=0,
            maximum=2,
        )
        timeout = _read_float(
            source,
            "LLM_TIMEOUT",
            default=120,
            minimum=0,
            minimum_inclusive=False,
        )
        max_tokens = _read_int(
            source,
            "LLM_MAX_TOKENS",
            default=8000,
            minimum=1,
        )

        return cls(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=SecretStr(api_key_value) if api_key_value is not None else None,
            temperature=temperature,
            timeout=timeout,
            max_tokens=max_tokens,
        )

    @classmethod
    def from_generic(cls, data: Mapping[str, Any]) -> Self:
        """Build settings from a generic flat dict (e.g. the settings DB)."""

        raw_provider = data.get("provider")
        if raw_provider is None or not str(raw_provider).strip():
            raise LLMConfigurationError("provider is required")
        try:
            provider = LLMProvider(str(raw_provider).strip().lower())
        except ValueError as error:
            supported = ", ".join(p.value for p in LLMProvider)
            raise LLMConfigurationError(
                f"provider must be one of: {supported}"
            ) from error

        model = str(data.get("model") or "").strip()
        if not model:
            raise LLMConfigurationError("model is required")

        spec = _PROVIDER_SPECS[provider]
        base_url = str(data.get("base_url") or "").strip() or None
        api_key = str(data.get("api_key") or "").strip() or None

        if spec.requires_base_url and base_url is None:
            raise LLMConfigurationError("base_url is required")
        if base_url is not None:
            _validate_http_url(base_url, "base_url")
        if spec.requires_api_key and api_key is None:
            raise LLMConfigurationError("api_key is required")

        try:
            temperature = float(data.get("temperature", 0.2))
            timeout = float(data.get("timeout", 120))
            max_tokens = int(data.get("max_tokens", 8000))
        except (TypeError, ValueError) as error:
            raise LLMConfigurationError(
                "temperature, timeout, and max_tokens must be numbers"
            ) from error

        return cls(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=SecretStr(api_key) if api_key is not None else None,
            temperature=temperature,
            timeout=timeout,
            max_tokens=max_tokens,
        )


@dataclass(frozen=True, slots=True)
class _ProviderSpec:
    model_env: str
    base_url_env: str | None
    api_key_env: str | None
    model_prefix: str | None
    requires_api_key: bool = True
    requires_base_url: bool = False


_PROVIDER_SPECS: dict[LLMProvider, _ProviderSpec] = {
    LLMProvider.LOCAL: _ProviderSpec(
        model_env="LOCAL_MODEL",
        base_url_env="LOCAL_BASE_URL",
        api_key_env="LOCAL_API_KEY",
        model_prefix=None,
        requires_api_key=False,
        requires_base_url=True,
    ),
    LLMProvider.OPENAI: _ProviderSpec(
        model_env="OPENAI_MODEL",
        base_url_env="OPENAI_BASE_URL",
        api_key_env="OPENAI_API_KEY",
        model_prefix="openai",
    ),
    LLMProvider.OPENROUTER: _ProviderSpec(
        model_env="OPENROUTER_MODEL",
        base_url_env="OPENROUTER_BASE_URL",
        api_key_env="OPENROUTER_API_KEY",
        model_prefix="openrouter",
    ),
    LLMProvider.ANTHROPIC: _ProviderSpec(
        model_env="ANTHROPIC_MODEL",
        base_url_env="ANTHROPIC_BASE_URL",
        api_key_env="ANTHROPIC_API_KEY",
        model_prefix="anthropic",
    ),
    LLMProvider.GROQ: _ProviderSpec(
        model_env="GROQ_MODEL",
        base_url_env="GROQ_BASE_URL",
        api_key_env="GROQ_API_KEY",
        model_prefix="groq",
    ),
    LLMProvider.DEEPSEEK: _ProviderSpec(
        model_env="DEEPSEEK_MODEL",
        base_url_env="DEEPSEEK_BASE_URL",
        api_key_env="DEEPSEEK_API_KEY",
        model_prefix="deepseek",
    ),
    LLMProvider.GOOGLE: _ProviderSpec(
        model_env="GOOGLE_MODEL",
        base_url_env=None,
        api_key_env="GOOGLE_API_KEY",
        model_prefix="gemini",
    ),
}


def create_llm(settings: LLMSettings) -> BaseLLM:
    """Create a CrewAI LLM for the selected provider without making a request."""

    spec = _PROVIDER_SPECS[settings.provider]
    kwargs: dict[str, object] = {
        "model": _qualified_model(settings.model, spec.model_prefix),
        "temperature": settings.temperature,
    }

    if settings.provider is not LLMProvider.GOOGLE:
        kwargs["timeout"] = settings.timeout

    if settings.provider is LLMProvider.GOOGLE:
        kwargs["max_output_tokens"] = settings.max_tokens
    else:
        kwargs["max_tokens"] = settings.max_tokens

    if settings.base_url is not None:
        kwargs["base_url"] = settings.base_url

    if settings.api_key is not None:
        kwargs["api_key"] = settings.api_key.get_secret_value()

    if settings.provider is LLMProvider.LOCAL:
        kwargs["custom_openai"] = True
        kwargs["api_key"] = settings.api_key.get_secret_value() if settings.api_key else "local"

    return LLM(**kwargs)  # type: ignore[arg-type,return-value]


def load_llm_settings() -> LLMSettings:
    """Resolve LLM settings, preferring the active DB config over env defaults."""

    from email_assistant.core.settings_store import SettingsStore

    config = SettingsStore().get_active_ai_config()
    if config is not None:
        return LLMSettings.from_generic(config)
    return LLMSettings.from_env()


def _read_provider(env: Mapping[str, str]) -> LLMProvider:
    raw_provider = env.get("LLM_PROVIDER")
    if raw_provider is None or not raw_provider.strip():
        raise LLMConfigurationError("LLM_PROVIDER is required")

    try:
        return LLMProvider(raw_provider.strip().lower())
    except ValueError as error:
        supported = ", ".join(provider.value for provider in LLMProvider)
        raise LLMConfigurationError(
            f"LLM_PROVIDER must be one of: {supported}"
        ) from error


def _required_value(env: Mapping[str, str], name: str) -> str:
    value = _optional_value(env, name)
    if value is None:
        raise LLMConfigurationError(f"{name} is required")
    return value


def _optional_value(
    env: Mapping[str, str],
    name: str | None,
) -> str | None:
    if name is None:
        return None
    value = env.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _read_float(
    env: Mapping[str, str],
    name: str,
    *,
    default: float,
    minimum: float,
    maximum: float | None = None,
    minimum_inclusive: bool = True,
) -> float:
    raw_value = env.get(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = float(raw_value)
    except ValueError as error:
        raise LLMConfigurationError(f"{name} must be a number") from error

    if not math.isfinite(value):
        raise LLMConfigurationError(f"{name} must be a finite number")

    below_minimum = value < minimum if minimum_inclusive else value <= minimum
    if below_minimum or (maximum is not None and value > maximum):
        raise LLMConfigurationError(f"{name} is outside the allowed range")
    return value


def _read_int(
    env: Mapping[str, str],
    name: str,
    *,
    default: int,
    minimum: int,
) -> int:
    raw_value = env.get(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = int(raw_value)
    except ValueError as error:
        raise LLMConfigurationError(f"{name} must be an integer") from error

    if value < minimum:
        raise LLMConfigurationError(f"{name} is outside the allowed range")
    return value


def _validate_http_url(url: str, name: str | None) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LLMConfigurationError(f"{name or 'BASE_URL'} must be a valid HTTP URL")


def _qualified_model(model: str, prefix: str | None) -> str:
    if prefix is None:
        return model
    qualified_prefix = f"{prefix}/"
    if model.lower().startswith(qualified_prefix):
        return model
    return f"{qualified_prefix}{model}"


__all__ = [
    "LLMConfigurationError",
    "LLMProvider",
    "LLMSettings",
    "create_llm",
    "load_llm_settings",
]
