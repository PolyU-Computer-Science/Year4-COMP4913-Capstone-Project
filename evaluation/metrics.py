"""Evaluation metrics (pure functions).

Each metric takes predictions + ground truth and returns a number or a
structured summary. These are model-agnostic — the runners feed them whatever
the predictor produced.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence


def accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    if not y_true:
        return 0.0
    return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)


def confusion_matrix(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str] | None = None
) -> dict[str, dict[str, int]]:
    label_set = list(labels) if labels else sorted(set(y_true) | set(y_pred))
    matrix = {label: {other: 0 for other in label_set} for label in label_set}
    for t, p in zip(y_true, y_pred):
        matrix.setdefault(t, {other: 0 for other in label_set})
        matrix.setdefault(p, {other: 0 for other in label_set})
        matrix[t][p] = matrix[t].get(p, 0) + 1
    return matrix


def _precision_recall_f1(
    y_true: Sequence[str], y_pred: Sequence[str], label: str
) -> tuple[float, float, float]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def macro_f1(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str] | None = None
) -> float:
    label_set = list(labels) if labels else sorted(set(y_true) | set(y_pred))
    if not label_set:
        return 0.0
    return sum(_precision_recall_f1(y_true, y_pred, l)[2] for l in label_set) / len(label_set)


def per_label_metrics(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str] | None = None
) -> dict[str, dict[str, float]]:
    label_set = list(labels) if labels else sorted(set(y_true) | set(y_pred))
    result = {}
    for label in label_set:
        precision, recall, f1 = _precision_recall_f1(y_true, y_pred, label)
        result[label] = {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
    return result


def topic_resolution_rate(resolved: Sequence[bool]) -> float:
    if not resolved:
        return 0.0
    return sum(1 for r in resolved if r) / len(resolved)


def recall_at_k(
    relevant: Sequence[set[str]], retrieved: Sequence[list[str]], k: int
) -> float:
    """Recall@K: fraction of relevant items found in top-k retrieved."""
    if not relevant:
        return 0.0
    hits = 0
    total = 0
    for rel, ret in zip(relevant, retrieved):
        top = set(ret[:k])
        hits += len(rel & top)
        total += len(rel)
    return hits / total if total else 0.0


def mean_reciprocal_rank(
    relevant: Sequence[set[str]], retrieved: Sequence[list[str]]
) -> float:
    if not relevant:
        return 0.0
    total = 0.0
    for rel, ret in zip(relevant, retrieved):
        for rank, item in enumerate(ret, start=1):
            if item in rel:
                total += 1.0 / rank
                break
    return total / len(relevant)


def exact_match_rate(
    expected: Sequence[dict[str, Any]], predicted: Sequence[dict[str, Any]]
) -> float:
    """Exact-match rate for dict-valued predictions (e.g. extracted fields)."""
    if not expected:
        return 0.0
    return sum(1 for e, p in zip(expected, predicted) if e == p) / len(expected)


def per_field_accuracy(
    expected: Sequence[dict[str, Any]], predicted: Sequence[dict[str, Any]]
) -> dict[str, float]:
    field_names = sorted({k for e in expected for k in e} | {k for p in predicted for k in p})
    result = {}
    for field in field_names:
        pairs = [(e.get(field), p.get(field)) for e, p in zip(expected, predicted)]
        denom = sum(1 for _, p in pairs if p is not None)
        correct = sum(1 for e, p in pairs if p is not None and e == p)
        result[field] = round(correct / denom, 4) if denom else 0.0
    return result
