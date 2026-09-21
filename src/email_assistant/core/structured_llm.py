"""Structured LLM client (OpenRouter MiMo runtime contract).

A unified path for requesting JSON-structured output from an LLM:

    raw response → JSON extraction → tolerant repair → Pydantic validation

Business validation (topic resolution, custom-field validation) stays in the
existing resolvers; this module only owns the schema contract, retry policy,
and observability metadata. The provider/model is ``xiaomi/mimo-v2.5-pro`` by
default (configured via env), but the client is transport-agnostic so tests
mock HTTP and never make paid calls.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv(override=False)

DEFAULT_MODEL = "xiaomi/mimo-v2.5-pro"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

T = TypeVar("T", bound=BaseModel)


class StructuredLLMError(RuntimeError):
    """Base class for structured-LLM errors."""


class StructuredLLMAuthError(StructuredLLMError):
    """401 — missing/invalid API key."""


class StructuredLLMPaymentError(StructuredLLMError):
    """402 — insufficient credits."""


class StructuredLLMRateLimitError(StructuredLLMError):
    """429 — rate limited."""


class StructuredLLMServerError(StructuredLLMError):
    """5xx — upstream server error."""


class StructuredLLMResponseError(StructuredLLMError):
    """Response could not be parsed/validated into the target model."""


@dataclass
class StructuredLLMResult(Generic[T]):
    """Result of a structured-LLM call with observability metadata."""

    data: T | None
    raw: str = ""
    valid: bool = False
    fallback_parser_used: bool = False
    repair_attempted: bool = False
    attempts: int = 0
    requested_model: str = ""
    returned_model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: float = 0.0
    error: str | None = None


_RETRYABLE_STATUS = {429}  # plus 5xx and network errors
_NON_RETRYABLE_STATUS = {401, 402}

_CODE_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json_object(text: str) -> dict | None:
    """Extract a JSON object from free-form text (strips fences, finds braces)."""
    if not text:
        return None
    fenced = _CODE_FENCE.search(text)
    candidate = fenced.group(1).strip() if fenced else text.strip()

    try:
        data = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        data = None
    if isinstance(data, dict):
        return data

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(candidate[start : end + 1])
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


class OpenRouterStructuredClient(Generic[T]):
    """Requests JSON output from an OpenAI-compatible chat endpoint."""

    provider = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 120.0,
        max_retries: int = 2,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        transport: Any = None,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max(0, int(max_retries))
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._transport = transport

    def _client(self):
        if self._transport is not None:
            return self._transport
        import httpx

        return httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )

    def generate(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
    ) -> StructuredLLMResult[T]:
        """Call the model and return a Pydantic-validated result.

        Retries only on transient failures (429 / 5xx / network). A malformed
        JSON response triggers one repair attempt via a stronger instruction.
        401/402 are surfaced immediately as configuration/payment errors.
        """
        start = time.perf_counter()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        result = StructuredLLMResult[T](
            data=None, requested_model=self.model
        )

        last_error: Exception | None = None
        attempts = 0
        repair_attempted = False

        while attempts <= self._max_retries:
            attempts += 1
            body = None
            try:
                body = self._post(messages, response_format={"type": "json_object"})
            except StructuredLLMAuthError:
                result.error = "authentication failed (401)"
                raise
            except StructuredLLMPaymentError:
                result.error = "insufficient credits (402)"
                raise
            except (StructuredLLMRateLimitError, StructuredLLMServerError) as error:
                last_error = error
                result.error = str(error)
                continue
            except StructuredLLMError as error:
                # Network/connection errors are transient.
                last_error = error
                result.error = str(error)
                continue

            # Successfully got a response body.
            result.returned_model = body.get("model")
            usage = body.get("usage") or {}
            result.prompt_tokens = usage.get("prompt_tokens")
            result.completion_tokens = usage.get("completion_tokens")
            result.total_tokens = usage.get("total_tokens")

            content = _message_content(body)
            result.raw = content

            parsed = extract_json_object(content)
            if parsed is not None:
                try:
                    result.data = response_model(**parsed)
                    result.valid = True
                    break
                except ValidationError:
                    # Schema-invalid but parseable JSON — not retryable.
                    result.error = "schema validation failed"
                    last_error = StructuredLLMResponseError(result.error)
                    break

            # Malformed JSON — one repair attempt with a stronger instruction.
            if not repair_attempted:
                repair_attempted = True
                result.repair_attempted = True
                messages[1] = {
                    "role": "user",
                    "content": (
                        "Your previous response was not valid JSON. Reply with "
                        "ONLY a single valid JSON object.\n\n" + user
                    ),
                }
                last_error = StructuredLLMResponseError("malformed JSON; repairing")
                result.error = str(last_error)
                continue

            result.fallback_parser_used = True
            last_error = StructuredLLMResponseError("could not extract JSON")
            result.error = str(last_error)
            break

        result.attempts = attempts
        result.latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if result.data is None and last_error is not None:
            result.error = str(last_error)
        return result

    def _post(self, messages: list[dict], response_format: dict) -> dict:
        import httpx

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "response_format": response_format,
        }
        client = self._client()
        try:
            response = client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as error:
            raise StructuredLLMError(f"request timed out: {error}") from error
        except httpx.RequestError as error:
            raise StructuredLLMError(f"request failed: {error}") from error

        status = response.status_code
        if status == 401:
            raise StructuredLLMAuthError("401 unauthorized")
        if status == 402:
            raise StructuredLLMPaymentError("402 payment required")
        if status == 429:
            raise StructuredLLMRateLimitError("429 rate limited")
        if status >= 500:
            raise StructuredLLMServerError(f"{status} server error")

        try:
            return response.json()
        except ValueError as error:
            raise StructuredLLMResponseError("invalid JSON response") from error


def _message_content(body: dict) -> str:
    choices = body.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or "")


def build_openrouter_structured_client() -> OpenRouterStructuredClient:
    """Build a structured client from environment variables."""
    import os

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    base_url = (
        os.environ.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL).strip()
        or DEFAULT_BASE_URL
    )
    if not api_key:
        raise StructuredLLMAuthError("OPENROUTER_API_KEY is not set")
    return OpenRouterStructuredClient(
        api_key=api_key, model=model, base_url=base_url
    )
