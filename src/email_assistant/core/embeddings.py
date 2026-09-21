"""Embedding client abstraction.

The indexing/retrieval layer should not depend on a specific embedding
provider. This module defines a small interface plus a deterministic local
implementation (hash-based) that works without external services — useful for
tests and offline demos. A real provider (OpenAI, Ollama, etc.) can be added
by implementing the same interface.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

_DIM = 256
_TOKEN_RE = re.compile(r"[a-z0-9]+")


class EmbeddingDimensionMismatch(ValueError):
    """Raised when comparing vectors of different dimensions."""


@dataclass(frozen=True)
class EmbeddingConfig:
    """Identity of an embedding provider/model, used for compatibility checks."""

    provider: str = "hashing"
    model: str = "hashing"
    dim: int = _DIM


class EmbeddingClient(ABC):
    """Embeds documents and queries into fixed-length vectors."""

    dim: int = _DIM

    @property
    def config(self) -> EmbeddingConfig:
        """The identity of this embedding client (provider/model/dim)."""
        return EmbeddingConfig(
            provider=self.provider,
            model=self.model,
            dim=self.dim,
        )

    provider: str = "hashing"
    model: str = "hashing"

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...


class HashingEmbeddingClient(EmbeddingClient):
    """Deterministic, offline embedding via hashed bag-of-tokens.

    Not semantically rich, but sufficient to validate the indexing/retrieval
    architecture and isolation guarantees without external dependencies.
    """

    dim = _DIM

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = _TOKEN_RE.findall((text or "").lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors.

    Raises ``EmbeddingDimensionMismatch`` if the vectors have different
    lengths — mismatched embeddings must never be silently compared.
    """
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        raise EmbeddingDimensionMismatch(
            f"Embedding dimension mismatch: {len(a)} vs {len(b)}"
        )
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embeddings_compatible(indexed: EmbeddingConfig, current: EmbeddingConfig) -> bool:
    """Return True if indexed vectors are compatible with the current client.

    Vectors are only comparable when provider, model and dimension all match.
    """
    return (
        indexed.provider == current.provider
        and indexed.model == current.model
        and indexed.dim == current.dim
    )


def get_embedding_client(provider: str = "hashing") -> EmbeddingClient:
    """Return an embedding client for the given provider string.

    Only ``hashing`` is implemented out of the box; other providers fall back
    to it so the pipeline never crashes on configuration.
    """
    if provider in ("hashing", "local", ""):
        return HashingEmbeddingClient()
    # Unknown provider: fall back to deterministic local embeddings.
    return HashingEmbeddingClient()
