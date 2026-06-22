from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_license.loader import load_license_records
from tessera_license.schema import LicenseFinding
from tessera_license.validator import validate_license_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[LicenseFinding]:
    return load_license_records(input_path, options)


def validate_records(records: list[LicenseFinding], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_license_records(records, options)


def write_artifacts(records: list[LicenseFinding], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(records, options)

    licenses_jsonl = ctx.output_dir / "licenses.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"

    write_jsonl(licenses_jsonl, [r.model_dump() for r in records])
    write_markdown(index_md, _render_index(records))
    write_markdown(validation_md, _render_validation(records, findings))
    write_markdown(coverage_md, _render_coverage(records))

    return [
        Artifact(name="licenses.jsonl", path=licenses_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
    ]


def _render_index(records: list[LicenseFinding]) -> str:
    lines = ["# License Inventory", ""]
    lines.append(f"- Declarations: {len(records)}")
    lines.append("")
    if not records:
        lines.append("_No license declarations found._")
        return "\n".join(lines) + "\n"
    lines.append("| Source | License | Category | Evidence | Path |")
    lines.append("|---|---|---|---|---|")
    for r in records:
        lines.append(f"| {r.source} | {r.license_id} | {r.category} | {r.evidence} | `{r.path}` |")
    return "\n".join(lines) + "\n"


def _render_validation(records: list[LicenseFinding], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Declarations: {len(records)}")
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


def _render_coverage(records: list[LicenseFinding]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Declarations: {len(records)}")
    if not records:
        return "\n".join(lines) + "\n"
    by_cat = Counter(r.category for r in records)
    by_id = Counter(r.license_id for r in records)
    lines.append("")
    lines.append("## By category")
    lines.append("")
    for cat, n in by_cat.most_common():
        lines.append(f"- {cat}: {n}")
    lines.append("")
    lines.append("## By license")
    lines.append("")
    for lid, n in by_id.most_common():
        lines.append(f"- `{lid}`: {n}")
    return "\n".join(lines) + "\n"
