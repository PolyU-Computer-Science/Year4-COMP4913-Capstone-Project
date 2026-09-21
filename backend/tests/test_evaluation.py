"""Phase 7 — evaluation dataset generator + validator tests."""

from __future__ import annotations

from pathlib import Path

from evaluation import generator
from evaluation.validators import (
    load_dataset,
    splits,
    validate_all,
    validate_dataset,
)

DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "evaluation" / "datasets" / "v1"


def test_generation_is_deterministic() -> None:
    a = generator.generate()
    b = generator.generate()
    assert a.keys() == b.keys()
    for name in a:
        assert a[name] == b[name]


def test_target_counts() -> None:
    datasets = generator.generate()
    for name, target in generator.COUNTS.items():
        assert len(datasets[name]) == target, name


def test_splits_are_20_80() -> None:
    datasets = generator.generate()
    for name, records in datasets.items():
        dev = sum(1 for r in records if r["split"] == "dev")
        test = sum(1 for r in records if r["split"] == "test")
        assert dev + test == len(records)
        assert dev > 0 and test > 0
        # 20% dev within a reasonable tolerance.
        assert abs(dev / len(records) - 0.2) < 0.05, name


def test_committed_datasets_validate_clean() -> None:
    errors = validate_all(DATASET_DIR)
    assert errors == []


def test_classification_has_all_categories_and_topics() -> None:
    records = load_dataset("classification", DATASET_DIR)
    categories = {r["category"] for r in records}
    assert {"question", "incident", "problem", "task", "spam"} <= categories


def test_classification_has_hard_examples() -> None:
    records = load_dataset("classification", DATASET_DIR)
    # Typo example exists.
    assert any("pasword" in r["body"] for r in records)
    # Quoted-thread example exists.
    assert any(r["body"].startswith(">>>") for r in records)
    # Spam exists.
    assert any(r["category"] == "spam" for r in records)


def test_retrieval_has_unanswerable() -> None:
    records = load_dataset("retrieval", DATASET_DIR)
    unanswerable = [r for r in records if not r["answerable"]]
    assert len(unanswerable) > 0
    # Roughly ~20% unanswerable.
    assert 0.1 < len(unanswerable) / len(records) < 0.3


def test_conflicting_knowledge_facts_are_distinct() -> None:
    from evaluation.fixtures import KNOWLEDGE

    support_text = " ".join(s["content"] for s in KNOWLEDGE["support"])
    sales_text = " ".join(s["content"] for s in KNOWLEDGE["sales"])
    assert "SUP-4821" in support_text
    assert "SAL-9913" in sales_text
    assert "SUP-4821" not in sales_text
    assert "SAL-9913" not in support_text


def test_tool_planning_support_mailbox_never_requires_tool() -> None:
    records = load_dataset("tool_planning", DATASET_DIR)
    for r in records:
        if r["mailbox"] == "support":
            assert r["tool_required"] is False
            assert r["expected_connector"] == ""


def test_validator_detects_duplicate_id() -> None:
    records = [
        {"id": "x", "mailbox": "support", "split": "test", "category": "question", "topic": "refund", "subject": "s", "body": "b1"},
        {"id": "x", "mailbox": "support", "split": "test", "category": "question", "topic": "refund", "subject": "s2", "body": "b2"},
    ]
    errors = validate_dataset("classification", records)
    assert any("duplicate id" in e for e in errors)


def test_validator_detects_invalid_topic() -> None:
    records = [
        {"id": "x", "mailbox": "support", "split": "test", "category": "question", "topic": "nonexistent", "subject": "s", "body": "b"},
    ]
    errors = validate_dataset("classification", records)
    assert any("not valid" in e for e in errors)


def test_validator_detects_invalid_mailbox() -> None:
    records = [
        {"id": "x", "mailbox": "nope", "split": "test", "category": "question", "topic": "refund", "subject": "s", "body": "b"},
    ]
    errors = validate_dataset("classification", records)
    assert any("invalid mailbox" in e for e in errors)


def test_validator_detects_duplicate_body() -> None:
    records = [
        {"id": "a", "mailbox": "support", "split": "test", "category": "question", "topic": "refund", "subject": "s1", "body": "same body"},
        {"id": "b", "mailbox": "support", "split": "test", "category": "question", "topic": "refund", "subject": "s2", "body": "same body"},
    ]
    errors = validate_dataset("classification", records)
    assert any("duplicate body" in e for e in errors)
