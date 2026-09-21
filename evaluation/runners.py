"""Evaluation runners.

A runner consumes a dataset split and a *predictor* (a callable that produces
model output for each record), then produces raw per-record results plus a
metrics summary. Runners are model-agnostic: tests inject fake predictors, and
the real MiMo/OpenRouter predictors are thin adapters over the runtime clients.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from evaluation import metrics
from evaluation.schemas import (
    ClassificationRecord,
    DraftingRecord,
    FieldExtractionRecord,
    RetrievalRecord,
    SafetyRecord,
    ToolPlanningRecord,
)


@dataclass
class RunResult:
    """Raw per-record results + a metrics summary for one dataset."""

    dataset: str
    split: str
    records: list[dict] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


# ---- predictor protocols (model-agnostic) ----

class ClassificationPredictor(Protocol):
    def predict(self, subject: str, body: str) -> dict[str, Any]:
        """Return {"category": str, "topic": str, "topic_resolved": bool}."""
        ...


class FieldExtractionPredictor(Protocol):
    def extract(self, subject: str, body: str) -> dict[str, Any]:
        """Return {field_id: value}."""
        ...


class RetrievalPredictor(Protocol):
    def search(self, query: str, top_k: int) -> list[str]:
        """Return ordered list of source_ids."""
        ...


class DraftingPredictor(Protocol):
    def draft(self, subject: str, body: str, knowledge: str) -> str:
        """Return draft text."""
        ...


class SafetyPredictor(Protocol):
    def run(self, subject: str, body: str) -> dict[str, Any]:
        """Return observed behavior, e.g. {"accessed_sources": [...], "sent": bool, ...}."""
        ...


# ---- classification runner ----

def run_classification(
    records: list[dict], predictor: ClassificationPredictor
) -> RunResult:
    y_true_cat: list[str] = []
    y_pred_cat: list[str] = []
    y_true_topic: list[str] = []
    y_pred_topic: list[str] = []
    resolved: list[bool] = []
    raw: list[dict] = []

    for record in records:
        prediction = predictor.predict(record["subject"], record["body"])
        y_true_cat.append(record["category"])
        y_pred_cat.append(prediction.get("category", ""))
        y_true_topic.append(record["topic"])
        y_pred_topic.append(prediction.get("topic", ""))
        resolved.append(bool(prediction.get("topic_resolved")))
        raw.append({"id": record["id"], "prediction": prediction, "expected": record})

    summary = {
        "accuracy": round(metrics.accuracy(y_true_cat, y_pred_cat), 4),
        "macro_f1": round(metrics.macro_f1(y_true_cat, y_pred_cat), 4),
        "per_label": metrics.per_label_metrics(y_true_cat, y_pred_cat),
        "confusion_matrix": metrics.confusion_matrix(y_true_cat, y_pred_cat),
        "topic_accuracy": round(metrics.accuracy(y_true_topic, y_pred_topic), 4),
        "topic_resolution_rate": round(metrics.topic_resolution_rate(resolved), 4),
        "count": len(records),
    }
    return RunResult(dataset="classification", split="test", records=raw, summary=summary)


# ---- field extraction runner ----

def run_field_extraction(
    records: list[dict], predictor: FieldExtractionPredictor
) -> RunResult:
    expected: list[dict] = []
    predicted: list[dict] = []
    raw: list[dict] = []

    for record in records:
        prediction = predictor.extract(record["subject"], record["body"])
        expected.append(record["expected_fields"])
        predicted.append(prediction)
        raw.append({"id": record["id"], "prediction": prediction, "expected": record["expected_fields"]})

    summary = {
        "exact_match_rate": round(metrics.exact_match_rate(expected, predicted), 4),
        "per_field_accuracy": metrics.per_field_accuracy(expected, predicted),
        "count": len(records),
    }
    return RunResult(dataset="field_extraction", split="test", records=raw, summary=summary)


# ---- retrieval runner ----

def run_retrieval(records: list[dict], predictor: RetrievalPredictor, top_k: int = 5) -> RunResult:
    relevant: list[set[str]] = []
    retrieved: list[list[str]] = []
    raw: list[dict] = []

    for record in records:
        results = predictor.search(record["query"], top_k)
        relevant.append(set(record["relevant_source_ids"]))
        retrieved.append(results)
        raw.append({"id": record["id"], "prediction": results, "expected": record["relevant_source_ids"]})

    ks = [1, 3, 5]
    recall = {f"recall@{k}": round(metrics.recall_at_k(relevant, retrieved, k), 4) for k in ks}
    summary = {
        **recall,
        "mrr": round(metrics.mean_reciprocal_rank(relevant, retrieved), 4),
        "count": len(records),
    }
    return RunResult(dataset="retrieval", split="test", records=raw, summary=summary)


# ---- drafting (RAG) runner ----

def run_drafting(records: list[dict], predictor: DraftingPredictor) -> RunResult:
    raw: list[dict] = []
    covered = 0
    violated = 0
    total_required = 0
    total_forbidden = 0

    for record in records:
        draft = predictor.draft(record["subject"], record["body"], "")
        draft_lower = draft.lower()
        required_hits = sum(1 for f in record["required_facts"] if f.lower() in draft_lower)
        forbidden_hits = sum(1 for f in record["forbidden_claims"] if f.lower() in draft_lower)
        covered += required_hits
        violated += forbidden_hits
        total_required += len(record["required_facts"])
        total_forbidden += len(record["forbidden_claims"])
        raw.append({
            "id": record["id"], "draft": draft,
            "required_facts_covered": required_hits,
            "forbidden_claims_violated": forbidden_hits,
        })

    summary = {
        "required_fact_coverage": round(covered / total_required, 4) if total_required else 0.0,
        "unsupported_claim_rate": round(violated / total_forbidden, 4) if total_forbidden else 0.0,
        "count": len(records),
    }
    return RunResult(dataset="drafting", split="test", records=raw, summary=summary)


# ---- safety runner ----

def run_safety(records: list[dict], predictor: SafetyPredictor) -> RunResult:
    raw: list[dict] = []
    passed = 0

    for record in records:
        observed = predictor.run(record["subject"], record["body"])
        # A record passes if none of its must_not violations occurred and all must occurred.
        violations = [m for m in record["must_not"] if observed.get(m, False)]
        missing = [m for m in record["must"] if not observed.get(m, False)]
        ok = not violations and not missing
        if ok:
            passed += 1
        raw.append({"id": record["id"], "observed": observed, "violations": violations, "missing": missing})

    summary = {
        "pass_rate": round(passed / len(records), 4) if records else 0.0,
        "attack_success_rate": round(1 - passed / len(records), 4) if records else 0.0,
        "count": len(records),
    }
    return RunResult(dataset="safety", split="test", records=raw, summary=summary)


# ---- tool planning runner ----

def run_tool_planning(records: list[dict], predictor: Callable[[str, str], dict[str, Any]]) -> RunResult:
    raw: list[dict] = []
    correct_tool = 0
    correct_decision = 0

    for record in records:
        prediction = predictor(record["subject"], record["body"])
        tool_required = record["tool_required"]
        if bool(prediction.get("tool_required")) == tool_required:
            correct_decision += 1
        if tool_required and prediction.get("tool") == record["expected_connector"]:
            correct_tool += 1
        raw.append({"id": record["id"], "prediction": prediction, "expected": record})

    total_tool = sum(1 for r in records if r["tool_required"])
    summary = {
        "decision_accuracy": round(correct_decision / len(records), 4) if records else 0.0,
        "tool_selection_accuracy": round(correct_tool / total_tool, 4) if total_tool else 0.0,
        "count": len(records),
    }
    return RunResult(dataset="tool_planning", split="test", records=raw, summary=summary)
