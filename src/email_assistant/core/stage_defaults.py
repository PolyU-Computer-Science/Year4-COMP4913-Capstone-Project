"""YAML-backed defaults for per-stage settings (prompts & parameters).

The role/goal/backstory/prompt defaults come from the YAML agent/task
configuration. Database values override these at runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

_AGENTS = yaml.safe_load((_CONFIG_DIR / "agents.yaml").read_text())
_TASKS = yaml.safe_load((_CONFIG_DIR / "tasks.yaml").read_text())

_STAGE_MAP = {
    "classification": ("classifier", "classify_email_task"),
    "draft": ("drafter", "draft_reply_task"),
}


def _stage_defaults(stage: str) -> dict[str, Any]:
    agent_key, task_key = _STAGE_MAP[stage]
    agent = _AGENTS[agent_key]
    task = _TASKS[task_key]
    return {
        "role": str(agent.get("role", "")).strip(),
        "goal": str(agent.get("goal", "")).strip(),
        "backstory": str(agent.get("backstory", "")).strip(),
        "prompt": str(task.get("description", "")).strip(),
        "max_tokens": None,
        "temperature": None,
    }


def effective_stage_settings(stage: str, overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge YAML defaults with DB overrides (non-empty DB values win)."""
    merged = _stage_defaults(stage)
    for field in ("role", "goal", "backstory", "prompt"):
        value = overrides.get(field)
        if value:
            merged[field] = value
    merged["max_tokens"] = overrides.get("max_tokens")
    merged["temperature"] = overrides.get("temperature")
    return merged
