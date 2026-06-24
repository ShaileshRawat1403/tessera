from __future__ import annotations

from typing import Any

import yaml
from tessera_core.artifacts import write_markdown, write_yaml
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_workflow.schema import WorkflowDefinition
from tessera_workflow.validator import validate_workflow_records


def load_records(input_path: Any, options: dict[str, Any]) -> list[WorkflowDefinition]:
    from tessera_workflow.loader import load_workflow_records
    return load_workflow_records(input_path, options)


def validate_records(
    records: list[WorkflowDefinition],
    options: dict[str, Any],
) -> list[ValidationFinding]:
    return validate_workflow_records(records, options)


def write_artifacts(
    records: list[WorkflowDefinition],
    ctx: RunContext,
    options: dict[str, Any],
) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(records, options)

    manifest_path = ctx.output_dir / "workflow_manifest.yaml"
    report_path = ctx.output_dir / "governance_report.md"

    manifests = [r.model_dump() for r in records]
    write_yaml(manifest_path, manifests if len(manifests) != 1 else manifests[0])
    write_markdown(report_path, _render_report(records, findings, options))

    return [
        Artifact(name="workflow_manifest.yaml", path=manifest_path, kind="yaml"),
        Artifact(name="governance_report.md", path=report_path, kind="markdown"),
    ]


def _render_report(
    records: list[WorkflowDefinition],
    findings: list[ValidationFinding],
    options: dict[str, Any],
) -> str:
    lines = ["# Governance Report", ""]

    sources = options.get("_source_files", [])
    lines.append(f"- Files scanned: {len(sources)}")
    lines.append(f"- Workflows validated: {len(records)}")
    lines.append(f"- Findings: {len(findings)}")
    lines.append("")

    if records:
        lines.append("## Workflows")
        lines.append("")
        for wf in records:
            gate_count = len(wf.review_gates)
            fence = "yes" if wf.recursion_fence else "NO"
            hash_inv = len(wf.evidence_policy.hash_invariant_steps)
            lines.append(f"### `{wf.name}` v{wf.version}")
            lines.append("")
            lines.append(f"- Steps: {len(wf.steps)}")
            lines.append(f"- Adapters required: {len(wf.required_adapters)}")
            lines.append(f"- Review gates: {gate_count}")
            lines.append(f"- Recursion fence: {fence}")
            lines.append(f"- Hash invariant steps: {hash_inv}")
            lines.append(f"- Promotion rule: `{wf.promotion_rule}`")
            lines.append("")
            lines.append("| # | Step | Adapter | Outputs |")
            lines.append("|---|------|---------|---------|")
            for i, step in enumerate(wf.steps, 1):
                outs = ", ".join(step.outputs) if step.outputs else "(none)"
                lines.append(f"| {i} | `{step.name}` | `{step.adapter}` | {outs} |")
            lines.append("")

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    infos = [f for f in findings if f.severity == "info"]

    if errors or warnings or infos:
        lines.append("## Findings")
        lines.append("")
        for f in findings:
            field_part = f" [{f.field}]" if f.field else ""
            lines.append(f"- **{f.severity.upper()}** `{f.code}`{field_part}: {f.message}")
        lines.append("")

    parse_errors = options.get("_parse_errors", [])
    if parse_errors:
        lines.append("## Parse Errors")
        lines.append("")
        for err in parse_errors:
            lines.append(f"- `{err.get('file', '?')}`: {err['error']}")
        lines.append("")

    return "\n".join(lines)
