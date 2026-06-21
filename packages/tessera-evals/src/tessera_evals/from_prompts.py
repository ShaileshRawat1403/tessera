"""Ingest a prompts-pack ``examples.jsonl`` into canonical eval records.

This module reads the documented prompt-examples interchange format. It does
NOT import ``tessera_prompts``: the two packs share a data contract (the shape
of ``examples.jsonl``), not code. The interchange shape, per prompt example row:

    {
      "id": "refund_window::ex_1",
      "prompt_name": "refund_window",
      "prompt_version": "1.0.0",
      "input_variables": {"customer_name": "Maya", ...},
      "rendered_prompt": "Hi Maya, ...",
      "expected": "...",            # may be null
      "notes": ""
    }

Only ``id`` and one of ``rendered_prompt`` / ``input_variables`` are required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tessera_evals.rubrics import default_rubric
from tessera_evals.schema import EvalRecord

EXAMPLES_FILENAME = "examples.jsonl"


def resolve_examples_path(input_path: Path) -> Path:
    """Accept either the examples.jsonl file or a prompt-pack directory holding it."""
    if input_path.is_dir():
        candidate = input_path / EXAMPLES_FILENAME
        if candidate.exists():
            return candidate
        raise ValueError(f"{input_path}: no {EXAMPLES_FILENAME} found in directory")
    return input_path


def load_prompt_examples(input_path: Path, options: dict[str, Any]) -> list[EvalRecord]:
    """Map prompt-example rows into EvalRecords.

    Stashes per-row notes and a source marker in ``options`` so the existing
    validate/write path works unchanged. Sets empty detection/analysis maps so
    the quality report renderer degrades gracefully (no column-detection table).
    """
    path = resolve_examples_path(input_path)
    task_type = options.get("task_type", "generic")

    rows: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            parse_errors.append({"line": str(lineno), "error": str(exc)})

    notes: list[dict[str, Any]] = []
    records: list[EvalRecord] = []
    seen_inputs: set[str] = set()

    for idx, row in enumerate(rows, start=1):
        source_id = str(row.get("id") or f"example_{idx}")
        user_input = _resolve_input(row)

        if not user_input:
            notes.append({"row": idx, "id": source_id, "code": "empty_input"})
            continue

        key = user_input.lower()
        if key in seen_inputs:
            notes.append({"row": idx, "id": source_id, "code": "duplicate_input"})
            continue
        seen_inputs.add(key)

        expected_text = str(row.get("expected") or "").strip()
        if expected_text:
            expected = {
                "mode": "reference",
                "reference_answer": expected_text,
                "review_status": "source_extracted",
            }
        else:
            expected = {
                "mode": options.get("golden_mode", "candidate"),
                "reference_answer": "",
                "review_status": "needs_human_review",
            }
            notes.append({"row": idx, "id": source_id, "code": "missing_expected_answer"})

        records.append(
            EvalRecord(
                id=source_id,
                task_type=task_type,
                input={"user_message": user_input},
                context={},
                expected=expected,
                rubric=default_rubric(task_type),
                metadata={
                    "source_row": idx,
                    "raw_id": source_id,
                    "origin": "prompts",
                    "prompt_name": row.get("prompt_name", ""),
                    "prompt_version": row.get("prompt_version", ""),
                },
            )
        )

    options["_raw_rows"] = rows
    options["_detections"] = {}
    options["_analyses"] = {}
    options["_notes"] = notes
    options["_source"] = "prompts"
    options["_parse_errors"] = parse_errors
    return records


def _resolve_input(row: dict[str, Any]) -> str:
    rendered = str(row.get("rendered_prompt") or "").strip()
    if rendered:
        return rendered
    variables = row.get("input_variables")
    if isinstance(variables, dict) and variables:
        return " ".join(f"{k}={v}" for k, v in variables.items()).strip()
    return ""
