from __future__ import annotations

import csv
from pathlib import Path
from typing import Any
from uuid import uuid4

from systemsdk_core.artifacts import write_csv, write_jsonl, write_markdown, write_yaml
from systemsdk_core.models import QualityFinding

from systemsdk_evals.schema import CompileOptions, EvalRecord

INPUT_CANDIDATES = ["question", "query", "input", "prompt", "user_message", "message", "text"]
EXPECTED_CANDIDATES = ["golden_answer", "expected", "expected_answer", "answer", "approved_answer", "final_resolution"]
CONTEXT_CANDIDATES = ["context", "source", "policy", "document", "source_text", "retrieved_context"]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pick_column(headers: list[str], preferred: str | None, candidates: list[str]) -> str | None:
    if preferred and preferred in headers:
        return preferred
    normalized = {h.lower().strip(): h for h in headers}
    for c in candidates:
        if c in normalized:
            return normalized[c]
    return None


def compile_rows(rows: list[dict[str, str]], options: CompileOptions) -> tuple[list[EvalRecord], list[dict[str, Any]], list[QualityFinding]]:
    headers = list(rows[0].keys()) if rows else []
    input_col = pick_column(headers, options.input_column, INPUT_CANDIDATES)
    expected_col = pick_column(headers, options.expected_column, EXPECTED_CANDIDATES)
    context_col = pick_column(headers, options.context_column, CONTEXT_CANDIDATES)

    findings: list[QualityFinding] = []
    if not input_col:
        findings.append(QualityFinding(level="error", code="missing_input_column", message="No input/question column was detected."))
        return [], [], findings

    records: list[EvalRecord] = []
    golden_candidates: list[dict[str, Any]] = []
    seen_inputs: set[str] = set()

    for idx, row in enumerate(rows, start=1):
        source_id = row.get("id") or row.get("ticket_id") or row.get("conversation_id") or f"row_{idx}"
        user_input = (row.get(input_col) or "").strip()
        expected_text = (row.get(expected_col) or "").strip() if expected_col else ""
        context_text = (row.get(context_col) or "").strip() if context_col else ""

        if not user_input:
            findings.append(QualityFinding(level="warning", code="empty_input", message="Input is empty.", record_id=str(source_id)))
            continue

        if user_input.lower() in seen_inputs:
            findings.append(QualityFinding(level="warning", code="duplicate_input", message="Duplicate input detected.", record_id=str(source_id)))
            continue
        seen_inputs.add(user_input.lower())

        expected: dict[str, Any]
        if expected_text:
            expected = {"mode": "reference", "reference_answer": expected_text, "review_status": "source_extracted"}
        else:
            expected = {"mode": options.golden_mode, "reference_answer": "", "review_status": "needs_human_review"}
            findings.append(QualityFinding(level="warning", code="missing_expected_answer", message="No expected answer found; candidate review required.", record_id=str(source_id)))

        record = EvalRecord(
            id=str(source_id),
            task_type=options.task_type,
            input={"user_message": user_input},
            context={"source_text": context_text} if context_text else {},
            expected=expected,
            rubric=default_rubric(options.task_type),
            metadata={"source_row": idx, "raw_id": str(source_id)},
        )
        records.append(record)
        golden_candidates.append({
            "id": record.id,
            "input": user_input,
            "candidate_golden_answer": expected_text,
            "source_evidence": context_text,
            "review_status": expected["review_status"],
        })

    return records, golden_candidates, findings


def default_rubric(task_type: str) -> dict[str, Any]:
    return {
        "task_type": task_type,
        "dimensions": [
            "correctness",
            "completeness",
            "groundedness",
            "safety_or_policy_fit",
        ],
        "must": [
            "answer the user request directly",
            "use available context when context is provided",
            "avoid unsupported claims",
        ],
        "must_not": [
            "invent facts not present in the input or context",
            "ignore explicit user constraints",
        ],
    }


def write_eval_pack(input_path: Path, output_dir: Path, task_type: str, input_column: str | None = None, expected_column: str | None = None, context_column: str | None = None) -> dict[str, Path | int]:
    rows = load_csv(input_path)
    options = CompileOptions(
        task_type=task_type,
        input_column=input_column,
        expected_column=expected_column,
        context_column=context_column,
    )
    records, golden_candidates, findings = compile_rows(rows, options)

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "dataset.jsonl"
    golden_path = output_dir / "golden_candidates.csv"
    rubric_path = output_dir / "rubric.yaml"
    quality_path = output_dir / "data_quality_report.md"
    coverage_path = output_dir / "coverage_report.md"

    write_jsonl(dataset_path, [r.model_dump() for r in records])
    write_csv(golden_path, golden_candidates)
    write_yaml(rubric_path, default_rubric(task_type))
    write_markdown(quality_path, render_quality_report(rows, records, findings))
    write_markdown(coverage_path, render_coverage_report(records))

    return {
        "raw_records": len(rows),
        "compiled_records": len(records),
        "findings": len(findings),
        "dataset": dataset_path,
        "golden_candidates": golden_path,
        "rubric": rubric_path,
        "quality_report": quality_path,
        "coverage_report": coverage_path,
    }


def render_quality_report(rows: list[dict[str, str]], records: list[EvalRecord], findings: list[QualityFinding]) -> str:
    lines = ["# Data Quality Report", "", f"Raw records: {len(rows)}", f"Compiled records: {len(records)}", f"Findings: {len(findings)}", ""]
    if findings:
        lines.append("## Findings")
        for finding in findings:
            rid = f" `{finding.record_id}`" if finding.record_id else ""
            lines.append(f"- **{finding.level.upper()}** `{finding.code}`{rid}: {finding.message}")
    return "\n".join(lines) + "\n"


def render_coverage_report(records: list[EvalRecord]) -> str:
    by_task: dict[str, int] = {}
    needs_review = 0
    for record in records:
        by_task[record.task_type] = by_task.get(record.task_type, 0) + 1
        if record.expected.get("review_status") == "needs_human_review":
            needs_review += 1
    lines = ["# Coverage Report", ""]
    for task, count in by_task.items():
        lines.append(f"- `{task}`: {count} examples")
    lines.append(f"- Needs human review: {needs_review}")
    return "\n".join(lines) + "\n"
