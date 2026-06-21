from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_csv, write_jsonl, write_markdown, write_yaml
from tessera_core.detect import (
    ColumnAnalysis,
    ColumnDetection,
    analyze_column,
    detect_by_content,
    detect_column,
)
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_evals.rubrics import default_rubric
from tessera_evals.schema import EvalRecord

INPUT_CANDIDATES = [
    "question",
    "query",
    "input",
    "prompt",
    "user_message",
    "message",
    "text",
    "user_input",
    "user_query",
    "user_request",
    "request",
    "ask",
    "inquiry",
    "issue",
    "complaint",
    "ticket",
    "body",
    "question_text",
]
EXPECTED_CANDIDATES = [
    "golden_answer",
    "expected",
    "expected_answer",
    "expected_response",
    "answer",
    "approved_answer",
    "final_resolution",
    "resolution",
    "response",
    "ground_truth",
    "groundtruth",
    "label",
    "target",
    "correct_answer",
    "ideal_response",
    "reference",
    "reference_answer",
    "gold",
    "truth",
    "reply",
    "agent_response",
    "team_response",
]
CONTEXT_CANDIDATES = [
    "context",
    "source",
    "policy",
    "document",
    "source_text",
    "retrieved_context",
    "retrieved",
    "retrieved_snippet",
    "snippet",
    "passage",
    "knowledge",
    "kb",
    "kb_article",
    "doc",
    "documentation",
    "article",
    "background",
    "evidence",
    "citation",
    "reference_text",
]


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_eval_records(input_path: Path, options: dict[str, Any]) -> list[EvalRecord]:
    """Detect columns, deduplicate, and build EvalRecord objects.

    Side effect: stores raw rows, detections, and per-row notes in ``options``
    under private keys so validate_eval_records and write_eval_artifacts can
    reuse them without re-parsing the CSV.

    When ``options["source"] == "prompts"`` the input is a prompts-pack
    ``examples.jsonl`` (or a directory containing it) rather than a CSV; the
    prompt-examples interchange loader is used instead of column detection.
    """
    if options.get("source") == "prompts":
        from tessera_evals.from_prompts import load_prompt_examples

        return load_prompt_examples(input_path, options)

    rows = _load_csv(input_path)
    headers = list(rows[0].keys()) if rows else []
    task_type = options.get("task_type", "generic")

    detections: dict[str, ColumnDetection] = {
        "input": detect_column(headers, "input", INPUT_CANDIDATES, options.get("input_column")),
        "expected": detect_column(headers, "expected", EXPECTED_CANDIDATES, options.get("expected_column")),
        "context": detect_column(headers, "context", CONTEXT_CANDIDATES, options.get("context_column")),
    }

    if detections["input"].column is None and options.get("input_column") is None:
        already_taken = [d.column for d in detections.values() if d.column]
        fallback = detect_by_content(
            rows, headers, "input", INPUT_CANDIDATES, exclude_columns=already_taken
        )
        if fallback.column is not None:
            detections["input"] = fallback

    analyses: dict[str, ColumnAnalysis] = {}
    for name, det in detections.items():
        if det.column:
            analyses[name] = analyze_column(rows, det.column)

    notes: list[dict[str, Any]] = []
    records: list[EvalRecord] = []
    seen_inputs: set[str] = set()

    input_col = detections["input"].column
    expected_col = detections["expected"].column
    context_col = detections["context"].column

    if not input_col:
        options["_raw_rows"] = rows
        options["_detections"] = detections
        options["_analyses"] = analyses
        options["_notes"] = notes
        return []

    for idx, row in enumerate(rows, start=1):
        source_id = row.get("id") or row.get("ticket_id") or row.get("conversation_id") or f"row_{idx}"
        source_id = str(source_id)
        user_input = (row.get(input_col) or "").strip()
        expected_text = (row.get(expected_col) or "").strip() if expected_col else ""
        context_text = (row.get(context_col) or "").strip() if context_col else ""

        if not user_input:
            notes.append({"row": idx, "id": source_id, "code": "empty_input"})
            continue

        key = user_input.lower()
        if key in seen_inputs:
            notes.append({"row": idx, "id": source_id, "code": "duplicate_input"})
            continue
        seen_inputs.add(key)

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
                context={"source_text": context_text} if context_text else {},
                expected=expected,
                rubric=default_rubric(task_type),
                metadata={"source_row": idx, "raw_id": source_id},
            )
        )

    options["_raw_rows"] = rows
    options["_detections"] = detections
    options["_analyses"] = analyses
    options["_notes"] = notes
    return records


def validate_eval_records(
    records: list[EvalRecord],
    options: dict[str, Any],
) -> list[ValidationFinding]:
    """Turn per-row notes and detection failures into ValidationFinding objects."""
    findings: list[ValidationFinding] = []

    for err in options.get("_parse_errors", []):
        findings.append(
            ValidationFinding(
                severity="error",
                code="parse_error",
                message=f"line {err.get('line', '?')}: {err['error']}",
                field=None,
            )
        )

    # Column-detection findings apply only to the CSV source. The prompts
    # interchange source has a known field mapping, so skip them.
    if options.get("_source") != "prompts":
        detections: dict[str, ColumnDetection] = options.get("_detections", {})

        input_det = detections.get("input")
        if input_det is None or input_det.column is None:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="missing_input_column",
                    message="No input/question column was detected. Use --input-column to override.",
                    field="input",
                )
            )

        for field_name in ("expected", "context"):
            det = detections.get(field_name)
            if det and det.column is None:
                findings.append(
                    ValidationFinding(
                        severity="info",
                        code=f"missing_{field_name}_column",
                        message=f"No {field_name} column was detected.",
                        field=field_name,
                    )
                )
            elif det and 0 < det.confidence < 0.85:
                findings.append(
                    ValidationFinding(
                        severity="warning",
                        code=f"low_confidence_{field_name}_column",
                        message=(
                            f"{field_name.capitalize()} column '{det.column}' detected at "
                            f"confidence {det.confidence:.2f}. Use --{field_name}-column to override."
                        ),
                        field=field_name,
                        metadata={"confidence": det.confidence, "reason": det.reason},
                    )
                )

    message_map = {
        "empty_input": "Input is empty.",
        "duplicate_input": "Duplicate input dropped.",
        "missing_expected_answer": "No expected answer found; row requires human review.",
    }
    for note in options.get("_notes", []):
        findings.append(
            ValidationFinding(
                severity="warning",
                code=note["code"],
                message=message_map.get(note["code"], note["code"]),
                field=None,
                metadata={"row": note["row"], "id": note["id"]},
            )
        )

    return findings


def write_eval_artifacts(
    records: list[EvalRecord],
    ctx: RunContext,
    options: dict[str, Any],
) -> list[Artifact]:
    """Write dataset, golden candidates, rubric, and quality plus coverage reports."""
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    task_type = options.get("task_type", "generic")
    detections: dict[str, ColumnDetection] = options.get("_detections", {})
    analyses: dict[str, ColumnAnalysis] = options.get("_analyses", {})
    raw_rows: list[dict[str, str]] = options.get("_raw_rows", [])
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_eval_records(records, options)

    dataset_path = ctx.output_dir / "dataset.jsonl"
    golden_path = ctx.output_dir / "golden_candidates.csv"
    rubric_path = ctx.output_dir / "rubric.yaml"
    quality_path = ctx.output_dir / "data_quality_report.md"
    coverage_path = ctx.output_dir / "coverage_report.md"

    write_jsonl(dataset_path, [r.model_dump() for r in records])
    write_csv(golden_path, _golden_candidates(records))
    write_yaml(rubric_path, default_rubric(task_type))
    write_markdown(
        quality_path,
        _render_quality_report(raw_rows, records, findings, detections, analyses, options.get("_source")),
    )
    write_markdown(coverage_path, _render_coverage_report(records))

    return [
        Artifact(name="dataset.jsonl", path=dataset_path, kind="jsonl"),
        Artifact(name="golden_candidates.csv", path=golden_path, kind="csv"),
        Artifact(name="rubric.yaml", path=rubric_path, kind="yaml"),
        Artifact(name="coverage_report.md", path=coverage_path, kind="markdown"),
        Artifact(name="data_quality_report.md", path=quality_path, kind="markdown"),
    ]


def _golden_candidates(records: list[EvalRecord]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for record in records:
        out.append(
            {
                "id": record.id,
                "input": record.input.get("user_message", ""),
                "candidate_golden_answer": record.expected.get("reference_answer", ""),
                "source_evidence": record.context.get("source_text", ""),
                "review_status": record.expected.get("review_status", ""),
            }
        )
    return out


def _render_quality_report(
    raw_rows: list[dict[str, str]],
    records: list[EvalRecord],
    findings: list[ValidationFinding],
    detections: dict[str, ColumnDetection],
    analyses: dict[str, ColumnAnalysis],
    source: str | None = None,
) -> str:
    lines: list[str] = ["# Data Quality Report", ""]
    source_label = "prompts examples.jsonl" if source == "prompts" else "CSV"
    lines.append(f"- Source: {source_label}")
    lines.append(f"- Raw records: {len(raw_rows)}")
    lines.append(f"- Compiled records: {len(records)}")
    lines.append(f"- Findings: {len(findings)}")
    lines.append("")

    override_hint_needed = False
    if source == "prompts":
        lines.append("## Field Mapping (prompts source)")
        lines.append("")
        lines.append("Records were ingested from a prompts-pack `examples.jsonl`. Column")
        lines.append("detection does not apply; the field mapping is fixed:")
        lines.append("")
        lines.append("- input  <- `rendered_prompt` (falls back to `input_variables`)")
        lines.append("- expected <- `expected`")
        lines.append("")
    else:
        lines.append("## Column Detection")
        lines.append("")
        lines.append("| Field | Column | Confidence | Reason |")
        lines.append("|---|---|---:|---|")
        for name in ("input", "expected", "context"):
            det = detections.get(name)
            if det is None:
                continue
            column = det.column or "(none)"
            lines.append(f"| {name} | {column} | {det.confidence:.2f} | {det.reason} |")
            if det.confidence and det.confidence < 0.95:
                override_hint_needed = True
        lines.append("")

    if analyses:
        lines.append("## Column Analysis")
        lines.append("")
        lines.append("| Field | Column | Type | Completeness | Avg length | Max length | Distinct |")
        lines.append("|---|---|---|---:|---:|---:|---:|")
        for name in ("input", "expected", "context"):
            an = analyses.get(name)
            if an is None:
                continue
            lines.append(
                f"| {name} | {an.column} | {an.inferred_type} "
                f"| {an.completeness:.2f} | {an.avg_length:.1f} | {an.max_length} | {an.distinct} |"
            )
        lines.append("")

    duplicate_count = sum(1 for f in findings if f.code == "duplicate_input")
    empty_count = sum(1 for f in findings if f.code == "empty_input")
    needs_review = sum(1 for f in findings if f.code == "missing_expected_answer")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Duplicates dropped: {duplicate_count}")
    lines.append(f"- Empty inputs dropped: {empty_count}")
    lines.append(f"- Rows needing human review: {needs_review}")
    lines.append("")

    warnings_and_errors = [f for f in findings if f.severity in ("warning", "error")]
    if warnings_and_errors:
        lines.append("## Warnings")
        lines.append("")
        for f in warnings_and_errors[:50]:
            field_part = f" [{f.field}]" if f.field else ""
            lines.append(f"- **{f.severity.upper()}** `{f.code}`{field_part}: {f.message}")
        if len(warnings_and_errors) > 50:
            lines.append(f"- ... {len(warnings_and_errors) - 50} more warnings omitted")
        lines.append("")

    if override_hint_needed:
        lines.append("## Recommended Override")
        lines.append("")
        lines.append("If any detected column is wrong, rerun with explicit flags:")
        lines.append("")
        lines.append("```bash")
        cmd = ["tessera evals compile", "  --input <path>", "  --task <task_type>"]
        for name in ("input", "expected", "context"):
            det = detections.get(name)
            if det and det.column:
                cmd.append(f"  --{name}-column {det.column}")
        lines.append(" \\\n".join(cmd))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def _render_coverage_report(records: list[EvalRecord]) -> str:
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
