"""Custom field value validation.

Field definitions come from the mailbox's configured custom fields. Values are
stored as JSON and must be validated server-side — the backend is the
authority, not the frontend.
"""

from __future__ import annotations

import json
from typing import Any

FIELD_TYPES = {"text", "textarea", "number", "boolean", "select", "multiselect", "date"}


def validate_field_value(field: dict[str, Any], value: Any) -> tuple[bool, str]:
    """Validate a raw value against a field definition.

    Returns ``(ok, error_message)``. The value must be JSON-serialisable and
    conform to the field's type. For ``select``, the value must be one of the
    configured options. For ``required`` fields, the value must not be empty.
    """
    field_type = str(field.get("type") or "text")
    name = str(field.get("name") or "field")

    if value is None:
        if field.get("required"):
            return False, f"{name} is required"
        return True, ""

    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False, f"{name} has an invalid value"

    if field_type in ("text", "textarea", "date", "select"):
        if not isinstance(value, str):
            return False, f"{name} must be a string"
        if field_type == "date" and value.strip():
            if len(value.split("-")) != 3:
                return False, f"{name} must be a date (YYYY-MM-DD)"

    elif field_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, f"{name} must be a number"

    elif field_type == "boolean":
        if not isinstance(value, bool):
            return False, f"{name} must be a boolean"

    elif field_type == "multiselect":
        if not isinstance(value, list):
            return False, f"{name} must be a list"

    else:
        return False, f"{name} has an unsupported type: {field_type}"

    if field_type in ("select", "multiselect"):
        options = _parse_options(field.get("options"))
        if options:
            values = value if isinstance(value, list) else [value]
            for item in values:
                if item not in options:
                    return False, f"{name} value {item!r} is not an allowed option"

    return True, ""


def _parse_options(raw: str) -> list[str]:
    """Parse a comma-separated options string into a list."""
    if not raw:
        return []
    return [opt.strip() for opt in str(raw).split(",") if opt.strip()]
