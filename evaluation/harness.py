"""Evaluation harness CLI (Phase 8).

Runs a chosen experiment against a dataset split using an injected predictor,
then writes raw results and a summary JSON to ``evaluation/results/``.

The harness is model-agnostic: real predictors are thin adapters over the
runtime clients. For reproducible offline runs, tests inject fake predictors.
Raw results are kept separately from the summary so numbers can be re-derived.

Usage:
    uv run python -m evaluation.harness run <experiment> [--split test]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from evaluation import runners
from evaluation.validators import load_dataset

RESULTS_DIR = Path(__file__).parent / "results"
DATASET_DIR = Path(__file__).parent / "datasets" / "v1"

EXPERIMENTS = {
    "classification": "classification",
    "field_extraction": "field_extraction",
    "retrieval": "retrieval",
    "drafting": "drafting",
    "safety": "safety",
    "tool_planning": "tool_planning",
}


def run_experiment(
    experiment: str,
    records: list[dict],
    predictor: Any,
    **kwargs: Any,
) -> runners.RunResult:
    if experiment == "classification":
        return runners.run_classification(records, predictor)
    if experiment == "field_extraction":
        return runners.run_field_extraction(records, predictor)
    if experiment == "retrieval":
        return runners.run_retrieval(records, predictor, top_k=kwargs.get("top_k", 5))
    if experiment == "drafting":
        return runners.run_drafting(records, predictor)
    if experiment == "safety":
        return runners.run_safety(records, predictor)
    if experiment == "tool_planning":
        return runners.run_tool_planning(records, predictor)
    raise ValueError(f"unknown experiment: {experiment}")


def write_results(result: runners.RunResult, experiment: str, output_dir: Path | None = None) -> dict[str, Path]:
    output_dir = output_dir or RESULTS_DIR
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / f"{experiment}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_path = run_dir / f"{experiment}_raw.jsonl"
    with raw_path.open("w", encoding="utf-8") as f:
        for record in result.records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary_path = run_dir / "summary.json"
    summary = {
        "experiment": experiment,
        "split": result.split,
        "timestamp": timestamp,
        "metrics": result.summary,
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"raw": raw_path, "summary": summary_path}


def run_and_write(
    experiment: str,
    predictor: Any,
    split: str = "test",
    output_dir: Path | None = None,
    **kwargs: Any,
) -> runners.RunResult:
    records = load_dataset(experiment, DATASET_DIR)
    records = [r for r in records if r["split"] == split]
    result = run_experiment(experiment, records, predictor, **kwargs)
    write_results(result, experiment, output_dir)
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run an evaluation experiment")
    parser.add_argument("experiment", choices=EXPERIMENTS.keys())
    parser.add_argument("--split", default="test", choices=["dev", "test"])
    args = parser.parse_args(argv)

    print(
        f"Experiment '{args.experiment}' requires an injected predictor. "
        "Use the Python API (evaluation.harness.run_and_write) with a real "
        "predictor adapter, or write a script that imports it."
    )


if __name__ == "__main__":
    main()
