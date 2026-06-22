from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_openapi.loader import load_openapi_records
from tessera_openapi.schema import Endpoint, SpecInfo
from tessera_openapi.validator import validate_openapi_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[Endpoint]:
    return load_openapi_records(input_path, options)


def validate_records(endpoints: list[Endpoint], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_openapi_records(endpoints, options)


def write_artifacts(endpoints: list[Endpoint], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    info: SpecInfo = options.get("_info", SpecInfo())
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(endpoints, options)

    endpoints_jsonl = ctx.output_dir / "endpoints.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    surface_md = ctx.output_dir / "surface.md"

    write_jsonl(endpoints_jsonl, [e.model_dump() for e in endpoints])
    write_markdown(index_md, _render_index(endpoints, info))
    write_markdown(validation_md, _render_validation(endpoints, findings))
    write_markdown(coverage_md, _render_coverage(endpoints, info))
    write_markdown(surface_md, _render_surface(endpoints))

    return [
        Artifact(name="endpoints.jsonl", path=endpoints_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="surface.md", path=surface_md, kind="markdown"),
    ]


def _render_index(endpoints: list[Endpoint], info: SpecInfo) -> str:
    lines = ["# API Endpoint Catalog", ""]
    lines.append(f"- Title: {info.title or '(none)'}")
    lines.append(f"- API version: {info.version or '(none)'}")
    lines.append(f"- Spec version: {info.spec_version or '(unknown)'}")
    lines.append(f"- Endpoints: {len(endpoints)}")
    lines.append("")
    if not endpoints:
        lines.append("_No endpoints found._")
        return "\n".join(lines) + "\n"
    lines.append("| Method | Path | operationId | Tags | Responses | Secured |")
    lines.append("|---|---|---|---|---|:--:|")
    for e in endpoints:
        tags = ", ".join(e.tags)
        resp = ", ".join(e.responses)
        sec = "yes" if e.secured else "-"
        lines.append(f"| {e.method} | `{e.path}` | {e.operation_id or '-'} | {tags} | {resp} | {sec} |")
    return "\n".join(lines) + "\n"


def _render_validation(endpoints: list[Endpoint], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Endpoints: {len(endpoints)}")
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
            ep = f.metadata.get("endpoint", "") if f.metadata else ""
            who = f" `{ep}`" if ep else ""
            lines.append(f"- **{f.severity.upper()}** `{f.code}`{who}: {f.message}")
        if len(findings) > 200:
            lines.append(f"- ... {len(findings) - 200} more findings omitted")
    return "\n".join(lines)


def _render_coverage(endpoints: list[Endpoint], info: SpecInfo) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Endpoints: {len(endpoints)}")
    if not endpoints:
        return "\n".join(lines) + "\n"
    n = len(endpoints)
    with_id = sum(1 for e in endpoints if e.operation_id)
    with_summary = sum(1 for e in endpoints if e.summary)
    secured = sum(1 for e in endpoints if e.secured)
    deprecated = sum(1 for e in endpoints if e.deprecated)
    lines.append(f"- With operationId: {with_id} ({100*with_id/n:.0f}%)")
    lines.append(f"- With summary/description: {with_summary} ({100*with_summary/n:.0f}%)")
    lines.append(f"- Secured: {secured} ({100*secured/n:.0f}%)")
    lines.append(f"- Deprecated: {deprecated}")
    lines.append("")
    method_dist = Counter(e.method for e in endpoints)
    lines.append("## Methods")
    lines.append("")
    for m, c in method_dist.most_common():
        lines.append(f"- `{m}`: {c}")
    return "\n".join(lines) + "\n"


def _render_surface(endpoints: list[Endpoint]) -> str:
    by_tag: dict[str, list[Endpoint]] = defaultdict(list)
    for e in endpoints:
        if e.tags:
            for t in e.tags:
                by_tag[t].append(e)
        else:
            by_tag["(untagged)"].append(e)

    lines = ["# API Surface (by tag)", ""]
    if not endpoints:
        lines.append("_No endpoints._")
        return "\n".join(lines) + "\n"
    for tag in sorted(by_tag):
        eps = by_tag[tag]
        lines.append(f"## {tag} ({len(eps)})")
        lines.append("")
        for e in sorted(eps, key=lambda x: (x.path, x.method)):
            summary = f" — {e.summary}" if e.summary else ""
            lines.append(f"- `{e.method} {e.path}`{summary}")
        lines.append("")
    return "\n".join(lines)
