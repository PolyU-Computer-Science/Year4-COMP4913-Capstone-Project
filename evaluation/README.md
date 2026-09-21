# Evaluation Datasets — v1

This directory contains the synthetic, controlled evaluation datasets for the
Final Year Project, plus the fixtures, generator, and validators that produce
and verify them.

## Design principle

Ground-truth labels are **scenario-defined**: a mailbox/category/topic/field
scenario is fixed *first*, and a natural-language email is generated to be
consistent with it. The model under test (`xiaomi/mimo-v2.5-pro`) is never used
to generate or label the frozen test split — that would introduce benchmark
bias.

## Layout

```text
evaluation/
├── fixtures.py          # canonical mailboxes/topics/fields/knowledge/connectors
├── schemas.py           # Pydantic schemas for each record type
├── generator.py         # deterministic, seeded dataset generator
├── validators.py        # duplicate/reference/leakage checks
├── metrics.py           # accuracy / F1 / confusion / Recall@K / MRR / ...
├── runners.py           # model-agnostic experiment runners
├── predictors.py        # adapters bridging the harness to runtime clients
├── harness.py           # orchestration + raw/summary result writer
├── manifest.json        # dataset version, counts, splits, methodology
├── datasets/
│   └── v1/
│       ├── classification.jsonl
│       ├── field_extraction.jsonl
│       ├── retrieval.jsonl
│       ├── drafting.jsonl
│       ├── safety.jsonl
│       └── tool_planning.jsonl
└── results/             # (gitignored) raw runs + summary JSON
```

## Dataset summary

| Dataset           | Count | Purpose                                            |
|-------------------|------:|----------------------------------------------------|
| classification    |   400 | Category + topic (incl. typos, threads, spam)      |
| field_extraction  |   200 | Typed custom fields (missing/invalid/ambiguous)     |
| retrieval         |   120 | Mailbox-scoped retrieval (~20% unanswerable)        |
| drafting          |   100 | RAG drafting with required/forbidden facts          |
| safety            |    80 | Injection, cross-mailbox, tool, auto-send           |
| tool_planning     |    50 | MCP tool selection + argument planning              |

Total: **950** records. Each is deterministically split into ~20% dev / ~80%
frozen test.

## Conflicting knowledge (isolation testing)

The `support` and `sales` knowledge bases contain **intentionally conflicting
facts** (e.g. escalation codes `SUP-4821` vs `SAL-9913`), so cross-mailbox
isolation can be quantitatively verified: the correct mailbox must never
retrieve or use the other mailbox's facts.

## Reproduce

```bash
uv run python -m evaluation.generator     # regenerate datasets/v1/*.jsonl
uv run pytest backend/tests/test_evaluation.py backend/tests/test_evaluation_harness.py
```

Generation is seeded (`SEED = 20260921`), so the datasets are fully
reproducible.

## Running experiments (Phase 8)

The harness is model-agnostic. To run a real experiment, build a predictor
adapter (see `evaluation/predictors.py`) and call:

```python
from evaluation.harness import run_and_write
from evaluation.predictors import StructuredClassificationPredictor

result = run_and_write("classification", predictor)
print(result.summary)
```

Raw per-record results are written to `evaluation/results/<experiment>_<ts>/`
alongside a `summary.json`; the summary metrics are derived from the raw
records so results are reproducible. The `results/` directory is gitignored.

## Rules

- The **dev split** may be used for prompt/implementation tuning.
- The **test split** is frozen for final evaluation — do not tune against it.
- Never regenerate labels with the model being evaluated.
