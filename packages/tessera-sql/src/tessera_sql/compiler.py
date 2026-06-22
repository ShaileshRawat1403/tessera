from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_sql.loader import load_sql_records
from tessera_sql.schema import SqlStatement, SqlTable
from tessera_sql.validator import validate_sql_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[SqlStatement]:
    return load_sql_records(input_path, options)


def validate_records(statements: list[SqlStatement], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_sql_records(statements, options)


def write_artifacts(statements: list[SqlStatement], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    tables: list[SqlTable] = options.get("_tables", [])
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(statements, options)

    statements_jsonl = ctx.output_dir / "statements.jsonl"
    tables_jsonl = ctx.output_dir / "tables.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    tables_md = ctx.output_dir / "tables.md"

    write_jsonl(statements_jsonl, [s.model_dump() for s in statements])
    write_jsonl(tables_jsonl, [t.model_dump() for t in tables])
    write_markdown(index_md, _render_index(statements, tables, options))
    write_markdown(validation_md, _render_validation(statements, findings))
    write_markdown(coverage_md, _render_coverage(statements))
    write_markdown(tables_md, _render_tables(tables))

    return [
        Artifact(name="statements.jsonl", path=statements_jsonl, kind="jsonl"),
        Artifact(name="tables.jsonl", path=tables_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="tables.md", path=tables_md, kind="markdown"),
    ]


def _render_index(statements: list[SqlStatement], tables: list[SqlTable], options: dict[str, Any]) -> str:
    lines = ["# SQL Catalog", ""]
    lines.append(f"- Files: {options.get('_file_count', 0)}")
    lines.append(f"- Statements: {len(statements)}")
    lines.append(f"- Tables created: {len(tables)}")
    lines.append("")
    if not statements:
        lines.append("_No statements found._")
        return "\n".join(lines) + "\n"
    lines.append("| Kind | Target | File:Line |")
    lines.append("|---|---|---|")
    for s in statements:
        lines.append(f"| {s.kind} | {s.target or '-'} | `{s.file}:{s.lineno}` |")
    return "\n".join(lines) + "\n"


def _render_validation(statements: list[SqlStatement], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Statements: {len(statements)}")
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
        for f in findings[:200]:
            lines.append(f"- **{f.severity.upper()}** `{f.code}`: {f.message}")
    return "\n".join(lines)


def _render_coverage(statements: list[SqlStatement]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Statements: {len(statements)}")
    if not statements:
        return "\n".join(lines) + "\n"
    kind_dist = Counter(s.kind for s in statements)
    lines.append("")
    lines.append("## Statement kinds")
    lines.append("")
    for kind, n in kind_dist.most_common():
        lines.append(f"- `{kind}`: {n}")
    return "\n".join(lines) + "\n"


def _render_tables(tables: list[SqlTable]) -> str:
    lines = ["# Tables", ""]
    lines.append(f"- Count: {len(tables)}")
    lines.append("")
    if not tables:
        lines.append("_No CREATE TABLE statements found._")
        return "\n".join(lines) + "\n"
    for t in tables:
        pk = "yes" if t.has_primary_key else "NO"
        lines.append(f"## `{t.name}` (PK: {pk})")
        lines.append("")
        lines.append(f"- Source: `{t.file}:{t.lineno}`")
        lines.append(f"- Columns ({len(t.columns)}): {', '.join(f'`{c}`' for c in t.columns) or '(none parsed)'}")
        lines.append("")
    return "\n".join(lines)
