from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_api.loader import load_api_records
from tessera_api.schema import ApiRequest
from tessera_api.validator import validate_api_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[ApiRequest]:
    return load_api_records(input_path, options)


def validate_records(records: list[ApiRequest], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for err in options.get("_parse_errors", []):
        findings.append(
            ValidationFinding(
                severity="error",
                code="parse_error",
                message=f"failed to parse curl: {err['error']} (near: {err.get('preview', '')})",
                field=None,
                metadata={"source_file": err.get("source_file", "")},
            )
        )
    findings.extend(validate_api_records(records))
    return findings


def write_artifacts(
    records: list[ApiRequest],
    ctx: RunContext,
    options: dict[str, Any],
) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = (
        ctx.metadata.get("findings") or validate_records(records, options)
    )

    index_jsonl = ctx.output_dir / "index.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    redactions_md = ctx.output_dir / "redactions_report.md"

    write_jsonl(index_jsonl, [r.model_dump() for r in records])
    write_markdown(index_md, _render_index(records))
    write_markdown(validation_md, _render_validation(records, findings, options))
    write_markdown(coverage_md, _render_coverage(records))
    write_markdown(redactions_md, _render_redactions(records))

    return [
        Artifact(name="index.jsonl", path=index_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="redactions_report.md", path=redactions_md, kind="markdown"),
    ]


def _render_index(records: list[ApiRequest]) -> str:
    lines = ["# API Request Catalog", ""]
    lines.append(f"- Total requests: {len(records)}")
    lines.append("")
    if not records:
        lines.append("_No requests found._")
        return "\n".join(lines) + "\n"

    lines.append("| ID | Method | Host | Path | Auth | Body | Redactions |")
    lines.append("|---|---|---|---|---|---|---:|")
    for r in records:
        lines.append(
            f"| `{r.id}` | {r.method} | {r.host} | {r.path} "
            f"| {r.auth.kind} | {r.body_kind} | {len(r.redactions)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_validation(
    records: list[ApiRequest],
    findings: list[ValidationFinding],
    options: dict[str, Any],
) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Total requests: {len(records)}")
    lines.append(f"- Findings: {len(findings)}")
    lines.append(f"- Parse errors: {len(options.get('_parse_errors', []))}")
    lines.append("")

    by_severity = Counter(f.severity for f in findings)
    lines.append("## Severity Breakdown")
    lines.append("")
    for sev in ("error", "warning", "info"):
        lines.append(f"- {sev}: {by_severity.get(sev, 0)}")
    lines.append("")

    if findings:
        lines.append("## Findings")
        lines.append("")
        for f in findings[:200]:
            ident = f.metadata.get("id", "") if f.metadata else ""
            who = f" `{ident}`" if ident else ""
            field_part = f" [{f.field}]" if f.field else ""
            lines.append(f"- **{f.severity.upper()}** `{f.code}`{who}{field_part}: {f.message}")
        if len(findings) > 200:
            lines.append(f"- ... {len(findings) - 200} more findings omitted")
    return "\n".join(lines)


def _render_coverage(records: list[ApiRequest]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Total requests: {len(records)}")
    if not records:
        return "\n".join(lines) + "\n"

    method_dist = Counter(r.method for r in records)
    host_dist = Counter(r.host for r in records)
    auth_dist = Counter(r.auth.kind for r in records)
    insecure = sum(1 for r in records if r.scheme == "http")

    lines.append(f"- Insecure (http) requests: {insecure}")
    lines.append("")
    lines.append("## Methods")
    lines.append("")
    for method, count in method_dist.most_common():
        lines.append(f"- `{method}`: {count}")
    lines.append("")
    lines.append("## Hosts")
    lines.append("")
    for host, count in host_dist.most_common():
        lines.append(f"- `{host}`: {count}")
    lines.append("")
    lines.append("## Auth kinds")
    lines.append("")
    for kind, count in auth_dist.most_common():
        lines.append(f"- `{kind}`: {count}")
    return "\n".join(lines) + "\n"


def _render_redactions(records: list[ApiRequest]) -> str:
    lines = ["# Redactions Report", ""]
    total = sum(len(r.redactions) for r in records)
    lines.append(f"- Total redactions: {total}")
    lines.append("")
    lines.append("Every secret below was masked before any artifact was written. "
                 "Previews reveal at most a couple of leading characters and the length.")
    lines.append("")

    if total == 0:
        lines.append("_No secrets detected._")
        return "\n".join(lines) + "\n"

    kind_dist: Counter[str] = Counter()
    for r in records:
        for red in r.redactions:
            kind_dist[red.kind] += 1
    lines.append("## By kind")
    lines.append("")
    for kind, count in kind_dist.most_common():
        lines.append(f"- `{kind}`: {count}")
    lines.append("")

    lines.append("## Detail")
    lines.append("")
    lines.append("| Request | Location | Kind | Preview |")
    lines.append("|---|---|---|---|")
    for r in records:
        for red in r.redactions:
            lines.append(f"| `{r.id}` | {red.location} | {red.kind} | `{red.preview}` |")
    return "\n".join(lines) + "\n"
