"""OpenRouter embeddings client.

Implements the ``EmbeddingClient`` protocol against OpenRouter's
OpenAI-compatible ``/embeddings`` endpoint. The embedding dimension is
discovered from the first response — never hardcoded — so a model swap is
detected by the existing ``EmbeddingConfig(provider, model, dim)``
compatibility layer.

All network access goes through a pluggable transport (``httpx`` by default)
so tests can mock HTTP and never incur a paid call.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from email_assistant.core.embeddings import EmbeddingClient

load_dotenv(override=False)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3-embedding-8b"
DEFAULT_BATCH_SIZE = 32


class OpenRouterEmbeddingError(RuntimeError):
    """Base class for OpenRouter embedding errors."""


class OpenRouterAuthError(OpenRouterEmbeddingError):
    """401 — missing/invalid API key."""


class OpenRouterPaymentError(OpenRouterEmbeddingError):
    """402 — insufficient credits / payment required."""


class OpenRouterRateLimitError(OpenRouterEmbeddingError):
    """429 — rate limited."""


class OpenRouterServerError(OpenRouterEmbeddingError):
    """5xx — upstream provider / server error."""


class OpenRouterResponseError(OpenRouterEmbeddingError):
    """Malformed / missing / dimension-inconsistent response."""


class OpenRouterEmbeddingClient(EmbeddingClient):
    """Semantic embeddings via OpenRouter's /embeddings endpoint."""

    provider = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        batch_size: int = DEFAULT_BATCH_SIZE,
        transport: Any = None,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._batch_size = max(1, int(batch_size))
        self._dim = 0
        self._transport = transport

    @property
    def dim(self) -> int:
        """Discovered embedding dimension (0 until first successful call)."""
        return self._dim

    def _client(self):
        if self._transport is not None:
            return self._transport
        import httpx

        return httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )

    def _post(self, payload: dict) -> dict:
        import httpx

        client = self._client()
        try:
            response = client.post("/embeddings", json=payload)
        except httpx.TimeoutException as error:
            raise OpenRouterEmbeddingError(f"Embedding request timed out: {error}") from error
        except httpx.RequestError as error:
            raise OpenRouterEmbeddingError(f"Embedding request failed: {error}") from error

        status = response.status_code
        if status == 401:
            raise OpenRouterAuthError("OpenRouter authentication failed (401)")
        if status == 402:
            raise OpenRouterPaymentError("OpenRouter insufficient credits (402)")
        if status == 429:
            raise OpenRouterRateLimitError("OpenRouter rate limit exceeded (429)")
        if status >= 500:
            raise OpenRouterServerError(f"OpenRouter server error ({status})")
        if status >= 400:
            raise OpenRouterEmbeddingError(
                f"OpenRouter embedding error ({status}): {_snippet(response.text)}"
            )

        try:
            return response.json()
        except ValueError as error:
            raise OpenRouterResponseError("Invalid JSON response from OpenRouter") from error

    def _extract_vectors(self, body: dict, expected: int) -> list[list[float]]:
        data = body.get("data") or []
        if not data:
            raise OpenRouterResponseError("Empty embedding response")
        if len(data) != expected:
            raise OpenRouterResponseError(
                f"Expected {expected} embeddings, got {len(data)}"
            )

        vectors: list[list[float]] = []
        for item in data:
            embedding = item.get("embedding")
            if not embedding:
                raise OpenRouterResponseError("Missing embedding vector in response")
            vectors.append([float(x) for x in embedding])

        dims = {len(v) for v in vectors}
        if len(dims) != 1:
            raise OpenRouterResponseError("Inconsistent embedding dimensions in batch")
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        all_vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            body = self._post({"model": self.model, "input": batch})
            vectors = self._extract_vectors(body, len(batch))
            all_vectors.extend(vectors)

        if all_vectors:
            self._dim = len(all_vectors[0])
        return all_vectors

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_documents([text])
        if not vectors:
            raise OpenRouterResponseError("Empty embedding response for query")
        return vectors[0]


def _snippet(text: str) -> str:
    return (text or "")[:200]


def build_openrouter_embedding_client() -> OpenRouterEmbeddingClient:
    """Build an OpenRouter client from environment variables."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    base_url = (
        os.environ.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL).strip()
        or DEFAULT_BASE_URL
    )
    batch_size = int(os.environ.get("EMBEDDING_BATCH_SIZE", DEFAULT_BATCH_SIZE))
    if not api_key:
        from email_assistant.core.embeddings import EmbeddingConfigurationError

        raise EmbeddingConfigurationError(
            "EMBEDDING_PROVIDER=openrouter but OPENROUTER_API_KEY is not set"
        )
    return OpenRouterEmbeddingClient(
        api_key=api_key,
        model=model,
        base_url=base_url,
        batch_size=batch_size,
    )
