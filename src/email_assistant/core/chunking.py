"""Text chunking for knowledge indexing.

Splits a document into overlapping chunks. The first version prefers natural
boundaries (paragraphs, then sentences) and falls back to a fixed token window
when the text has no clear structure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")


@dataclass
class KnowledgeChunk:
    """A single chunk of a knowledge document."""

    index: int
    content: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


def approximate_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token, or word count if larger."""
    if not text:
        return 0
    words = len(text.split())
    chars = max(1, len(text) // 4)
    return max(words, chars)


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text)]
    return [p for p in parts if p]


def _split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENTENCE_SPLIT.split(text)]
    return [p for p in parts if p]


def chunk_text(
    text: str,
    target_tokens: int = 600,
    overlap_tokens: int = 100,
    metadata: dict[str, Any] | None = None,
) -> list[KnowledgeChunk]:
    """Chunk ``text`` into overlapping KnowledgeChunks.

    Prefers paragraph boundaries, then sentence boundaries, then falls back to
    a hard token window. ``overlap_tokens`` determines how much of the previous
    chunk is repeated at the start of the next.
    """
    if not text or not text.strip():
        return []

    normalized = text.strip()
    paragraphs = _split_paragraphs(normalized)

    # If a single paragraph is already within target, keep it as one chunk.
    if len(paragraphs) <= 1 and approximate_tokens(normalized) <= target_tokens:
        return [
            KnowledgeChunk(
                index=0,
                content=normalized,
                token_count=approximate_tokens(normalized),
                metadata=dict(metadata or {}),
            )
        ]

    sentences: list[str] = []
    for paragraph in paragraphs:
        if approximate_tokens(paragraph) <= target_tokens:
            sentences.append(paragraph)
        else:
            sentences.extend(_split_sentences(paragraph))

    chunks: list[KnowledgeChunk] = []
    current: list[str] = []
    current_tokens = 0
    overlap_words = overlap_tokens

    for sentence in sentences:
        sentence_tokens = approximate_tokens(sentence)
        if current and current_tokens + sentence_tokens > target_tokens:
            content = " ".join(current).strip()
            chunks.append(
                KnowledgeChunk(
                    index=len(chunks),
                    content=content,
                    token_count=approximate_tokens(content),
                    metadata=dict(metadata or {}),
                )
            )
            # Carry overlap: keep the tail of the current chunk.
            words = current[-1].split()
            tail = " ".join(words[-overlap_words:]) if overlap_words else ""
            current = [tail] if tail else []
            current_tokens = approximate_tokens(tail)
        current.append(sentence)
        current_tokens += sentence_tokens

    if current:
        content = " ".join(current).strip()
        if content:
            chunks.append(
                KnowledgeChunk(
                    index=len(chunks),
                    content=content,
                    token_count=approximate_tokens(content),
                    metadata=dict(metadata or {}),
                )
            )

    return chunks
