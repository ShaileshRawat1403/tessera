from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_tests.loader import load_test_records
from tessera_tests.schema import TestCase
from tessera_tests.validator import validate_test_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[TestCase]:
    return load_test_records(input_path, options)


def validate_records(cases: list[TestCase], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_test_records(cases, options)


def write_artifacts(cases: list[TestCase], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(cases, options)

    tests_jsonl = ctx.output_dir / "tests.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    not_running_md = ctx.output_dir / "not_running.md"

    write_jsonl(tests_jsonl, [c.model_dump() for c in cases])
    write_markdown(index_md, _render_index(cases, options))
    write_markdown(validation_md, _render_validation(cases, findings))
    write_markdown(coverage_md, _render_coverage(cases))
    write_markdown(not_running_md, _render_not_running(cases))

    return [
        Artifact(name="tests.jsonl", path=tests_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="not_running.md", path=not_running_md, kind="markdown"),
    ]


def _render_index(cases: list[TestCase], options: dict[str, Any]) -> str:
    lines = ["# Test Inventory", ""]
    lines.append(f"- Test files: {options.get('_file_count', 0)}")
    lines.append(f"- Tests: {len(cases)}")
    no_assert = sum(1 for c in cases if not c.has_assert and not c.is_skipped and not c.is_xfail)
    lines.append(f"- Tests with no assertions: {no_assert}")
    lines.append("")
    if not cases:
        lines.append("_No tests found._")
        return "\n".join(lines) + "\n"
    lines.append("| Test | Asserts | Skipped | Xfail | Param | Location |")
    lines.append("|---|---:|:--:|:--:|:--:|---|")
    for c in cases:
        lines.append(
            f"| `{c.qualname}` | {c.assertion_count} "
            f"| {'yes' if c.is_skipped else '-'} | {'yes' if c.is_xfail else '-'} "
            f"| {'yes' if c.is_parametrized else '-'} | `{c.file}:{c.lineno}` |"
        )
    return "\n".join(lines) + "\n"


def _render_validation(cases: list[TestCase], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Tests: {len(cases)}")
    lines.append(f"- Findings: {len(findings)}")
    lines.append("")
    by_sev = Counter(f.severity for f in findings)
    lines.append("## Severity Breakdown")
    lines.append("")
    for sev in ("error", "warning", "info"):
        lines.append(f"- {sev}: {by_sev.get(sev, 0)}")
    lines.append("")
    if findings:
        lines.append("## Findings")
        lines.append("")
        for f in findings[:300]:
            lines.append(f"- **{f.severity.upper()}** `{f.code}`: {f.message}")
    return "\n".join(lines)


def _render_coverage(cases: list[TestCase]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Tests: {len(cases)}")
    if not cases:
        return "\n".join(lines) + "\n"
    skipped = sum(1 for c in cases if c.is_skipped)
    xfail = sum(1 for c in cases if c.is_xfail)
    param = sum(1 for c in cases if c.is_parametrized)
    no_assert = sum(1 for c in cases if not c.has_assert and not c.is_skipped and not c.is_xfail)
    lines.append(f"- Skipped: {skipped}")
    lines.append(f"- Xfail: {xfail}")
    lines.append(f"- Parametrized: {param}")
    lines.append(f"- No assertions: {no_assert}")
    lines.append("")
    by_file = Counter(c.file for c in cases)
    lines.append("## Tests per file")
    lines.append("")
    for path, n in by_file.most_common():
        lines.append(f"- `{path}`: {n}")
    return "\n".join(lines) + "\n"


def _render_not_running(cases: list[TestCase]) -> str:
    inactive = [c for c in cases if c.is_skipped or c.is_xfail]
    lines = ["# Tests Not Effectively Running", ""]
    lines.append("Skipped and xfail tests — present but not protecting anything right now.")
    lines.append("")
    if not inactive:
        lines.append("_All discovered tests are active._")
        return "\n".join(lines) + "\n"
    for c in inactive:
        tag = "skip" if c.is_skipped else "xfail"
        lines.append(f"- **{tag}** `{c.qualname}` ({c.file}:{c.lineno})")
    return "\n".join(lines) + "\n"
