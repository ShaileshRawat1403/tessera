from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_todo.loader import load_todo_records
from tessera_todo.schema import TodoItem
from tessera_todo.validator import validate_todo_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[TodoItem]:
    return load_todo_records(input_path, options)


def validate_records(items: list[TodoItem], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_todo_records(items, options)


def write_artifacts(items: list[TodoItem], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(items, options)

    todos_jsonl = ctx.output_dir / "todos.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    by_owner_md = ctx.output_dir / "by_owner.md"

    write_jsonl(todos_jsonl, [it.model_dump() for it in items])
    write_markdown(index_md, _render_index(items, options))
    write_markdown(validation_md, _render_validation(items, findings))
    write_markdown(coverage_md, _render_coverage(items))
    write_markdown(by_owner_md, _render_by_owner(items))

    return [
        Artifact(name="todos.jsonl", path=todos_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="by_owner.md", path=by_owner_md, kind="markdown"),
    ]


def _render_index(items: list[TodoItem], options: dict[str, Any]) -> str:
    lines = ["# TODO / Marker Backlog", ""]
    lines.append(f"- Files scanned: {options.get('_file_count', 0)}")
    lines.append(f"- Markers: {len(items)}")
    high = sum(1 for it in items if it.priority == "high")
    lines.append(f"- High priority: {high}")
    lines.append("")
    if not items:
        lines.append("_No markers found._")
        return "\n".join(lines) + "\n"
    # high priority first, then by file
    ordered = sorted(items, key=lambda it: (0 if it.priority == "high" else 1, it.file, it.lineno))
    lines.append("| Priority | Marker | Owner | Location | Text |")
    lines.append("|---|---|---|---|---|")
    for it in ordered[:500]:
        lines.append(f"| {it.priority} | {it.marker} | {it.owner or '-'} | `{it.file}:{it.lineno}` | {it.text or ''} |")
    return "\n".join(lines) + "\n"


def _render_validation(items: list[TodoItem], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Markers: {len(items)}")
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
        if len(findings) > 300:
            lines.append(f"- ... {len(findings) - 300} more findings omitted")
    return "\n".join(lines)


def _render_coverage(items: list[TodoItem]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Markers: {len(items)}")
    if not items:
        return "\n".join(lines) + "\n"
    by_marker = Counter(it.marker for it in items)
    by_priority = Counter(it.priority for it in items)
    lines.append("")
    lines.append("## By priority")
    lines.append("")
    for pr in ("high", "normal", "low"):
        if by_priority.get(pr):
            lines.append(f"- {pr}: {by_priority[pr]}")
    lines.append("")
    lines.append("## By marker")
    lines.append("")
    for marker, n in by_marker.most_common():
        lines.append(f"- `{marker}`: {n}")
    lines.append("")
    by_file = Counter(it.file for it in items)
    lines.append("## Files with the most markers")
    lines.append("")
    for path, n in by_file.most_common(10):
        lines.append(f"- `{path}`: {n}")
    return "\n".join(lines) + "\n"


def _render_by_owner(items: list[TodoItem]) -> str:
    grouped: dict[str, list[TodoItem]] = defaultdict(list)
    for it in items:
        grouped[it.owner or "(unassigned)"].append(it)
    lines = ["# Markers by Owner", ""]
    for owner in sorted(grouped):
        group = grouped[owner]
        lines.append(f"## {owner} ({len(group)})")
        lines.append("")
        for it in sorted(group, key=lambda x: (x.file, x.lineno)):
            lines.append(f"- **{it.marker}** `{it.file}:{it.lineno}` — {it.text or '(no description)'}")
        lines.append("")
    return "\n".join(lines)
