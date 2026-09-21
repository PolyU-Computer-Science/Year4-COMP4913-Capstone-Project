"""Phase 8 — evaluation metrics + runners tests (offline, fake predictors)."""

from __future__ import annotations

from evaluation import metrics, runners


def test_accuracy() -> None:
    assert metrics.accuracy(["a", "b", "a"], ["a", "a", "a"]) == 2 / 3


def test_accuracy_empty() -> None:
    assert metrics.accuracy([], []) == 0.0


def test_macro_f1_balanced_classes() -> None:
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "b", "b", "b"]
    f1 = metrics.macro_f1(y_true, y_pred, labels=["a", "b"])
    assert 0.0 <= f1 <= 1.0


def test_confusion_matrix_shape() -> None:
    matrix = metrics.confusion_matrix(["a", "b"], ["a", "a"], labels=["a", "b"])
    assert matrix["a"]["a"] == 1
    assert matrix["b"]["a"] == 1


def test_per_label_metrics() -> None:
    result = metrics.per_label_metrics(["a", "a"], ["a", "a"], labels=["a"])
    assert result["a"]["f1"] == 1.0


def test_topic_resolution_rate() -> None:
    assert metrics.topic_resolution_rate([True, True, False]) == 2 / 3


def test_recall_at_k() -> None:
    relevant = [{"a", "b"}]
    retrieved = [["a", "x", "y"]]
    assert metrics.recall_at_k(relevant, retrieved, 1) == 0.5
    assert metrics.recall_at_k(relevant, retrieved, 3) == 0.5


def test_mean_reciprocal_rank() -> None:
    relevant = [{"a"}, {"b"}]
    retrieved = [["x", "a"], ["b"]]
    assert metrics.mean_reciprocal_rank(relevant, retrieved) == (0.5 + 1.0) / 2


def test_exact_match_rate() -> None:
    expected = [{"a": 1}, {"b": 2}]
    predicted = [{"a": 1}, {"b": 3}]
    assert metrics.exact_match_rate(expected, predicted) == 0.5


def test_per_field_accuracy() -> None:
    expected = [{"x": 1, "y": 2}]
    predicted = [{"x": 1, "y": None}]
    result = metrics.per_field_accuracy(expected, predicted)
    assert result["x"] == 1.0
    assert result["y"] == 0.0


# ---- runner tests ----


def test_run_classification_summary() -> None:
    records = [
        {"id": "1", "category": "question", "topic": "refund", "subject": "s", "body": "b"},
        {"id": "2", "category": "spam", "topic": "refund", "subject": "s", "body": "b"},
    ]

    class P:
        def predict(self, subject, body):
            return {"category": "question", "topic": "refund", "topic_resolved": True}

    result = runners.run_classification(records, P())
    assert result.summary["count"] == 2
    assert result.summary["accuracy"] == 0.5
    assert result.summary["topic_resolution_rate"] == 1.0


def test_run_retrieval_summary() -> None:
    records = [
        {"id": "1", "query": "q", "relevant_source_ids": ["a"], "answerable": True},
    ]

    class P:
        def search(self, query, top_k):
            return ["a", "b"]

    result = runners.run_retrieval(records, P(), top_k=5)
    assert result.summary["recall@1"] == 1.0
    assert result.summary["mrr"] == 1.0


def test_run_field_extraction() -> None:
    records = [
        {"id": "1", "expected_fields": {"order_id": "A"}, "subject": "s", "body": "b"},
    ]

    class P:
        def extract(self, subject, body):
            return {"order_id": "A"}

    result = runners.run_field_extraction(records, P())
    assert result.summary["exact_match_rate"] == 1.0


def test_run_drafting_measures_required_and_forbidden() -> None:
    records = [
        {
            "id": "1",
            "subject": "s",
            "body": "b",
            "required_facts": ["30 days"],
            "forbidden_claims": ["always approved"],
        },
    ]

    class P:
        def draft(self, subject, body, knowledge):
            return "Refund requests must be submitted within 30 days."

    result = runners.run_drafting(records, P())
    assert result.summary["required_fact_coverage"] == 1.0
    assert result.summary["unsupported_claim_rate"] == 0.0


def test_run_safety_pass_and_fail() -> None:
    records = [
        {"id": "1", "subject": "s", "body": "b", "must_not": ["leak"], "must": []},
        {"id": "2", "subject": "s", "body": "b", "must_not": ["leak"], "must": []},
    ]

    class P:
        def __init__(self):
            self.n = 0

        def run(self, subject, body):
            self.n += 1
            return {"leak": self.n == 1}  # first leaks, second doesn't

    result = runners.run_safety(records, P())
    assert result.summary["pass_rate"] == 0.5
    assert result.summary["attack_success_rate"] == 0.5


def test_run_tool_planning_decision() -> None:
    records = [
        {"id": "1", "subject": "s", "body": "b", "tool_required": True, "expected_connector": "mtr"},
        {"id": "2", "subject": "s", "body": "b", "tool_required": False, "expected_connector": ""},
    ]

    def predictor(subject, body):
        return {"tool_required": True, "tool": "mtr"}

    result = runners.run_tool_planning(records, predictor)
    assert result.summary["decision_accuracy"] == 0.5
