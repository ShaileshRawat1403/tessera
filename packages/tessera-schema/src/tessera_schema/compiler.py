from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_schema.loader import load_schema_records
from tessera_schema.schema import SchemaDoc
from tessera_schema.validator import validate_schema_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[SchemaDoc]:
    return load_schema_records(input_path, options)


def validate_records(docs: list[SchemaDoc], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_schema_records(docs, options)


def write_artifacts(docs: list[SchemaDoc], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(docs, options)

    schemas_jsonl = ctx.output_dir / "schemas.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"

    write_jsonl(schemas_jsonl, [d.model_dump() for d in docs])
    write_markdown(index_md, _render_index(docs, options))
    write_markdown(validation_md, _render_validation(docs, findings))
    write_markdown(coverage_md, _render_coverage(docs))

    return [
        Artifact(name="schemas.jsonl", path=schemas_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
    ]


def _render_index(docs: list[SchemaDoc], options: dict[str, Any]) -> str:
    lines = ["# JSON Schema Catalog", ""]
    lines.append(f"- Schemas: {len(docs)}")
    lines.append("")
    if not docs:
        lines.append("_No JSON Schema documents found._")
        return "\n".join(lines) + "\n"
    lines.append("| Schema | Type | Properties | Required | $defs | Title |")
    lines.append("|---|---|---:|---:|---:|---|")
    for d in sorted(docs, key=lambda x: x.path):
        lines.append(
            f"| `{d.path}` | {d.type or '-'} | {len(d.properties)} | {len(d.required)} "
            f"| {len(d.defs)} | {d.title or '-'} |"
        )
    return "\n".join(lines) + "\n"


def _render_validation(docs: list[SchemaDoc], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Schemas: {len(docs)}")
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


def _render_coverage(docs: list[SchemaDoc]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Schemas: {len(docs)}")
    if not docs:
        return "\n".join(lines) + "\n"
    by_type = Counter(d.type or "(none)" for d in docs)
    with_title = sum(1 for d in docs if d.title)
    with_version = sum(1 for d in docs if d.schema_version)
    lines.append(f"- With title: {with_title}")
    lines.append(f"- With $schema dialect: {with_version}")
    lines.append("")
    lines.append("## Root types")
    lines.append("")
    for t, n in by_type.most_common():
        lines.append(f"- `{t}`: {n}")
    return "\n".join(lines) + "\n"
