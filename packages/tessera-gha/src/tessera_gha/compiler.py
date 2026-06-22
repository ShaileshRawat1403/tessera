from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_gha.loader import load_gha_records
from tessera_gha.schema import WorkflowInfo, WorkflowItem
from tessera_gha.validator import validate_gha_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[WorkflowItem]:
    return load_gha_records(input_path, options)


def validate_records(items: list[WorkflowItem], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_gha_records(items, options)


def write_artifacts(items: list[WorkflowItem], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    infos: list[WorkflowInfo] = options.get("_infos", [])
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(items, options)

    items_jsonl = ctx.output_dir / "items.jsonl"
    workflows_jsonl = ctx.output_dir / "workflows.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"

    write_jsonl(items_jsonl, [i.model_dump() for i in items])
    write_jsonl(workflows_jsonl, [w.model_dump() for w in infos])
    write_markdown(index_md, _render_index(items, infos))
    write_markdown(validation_md, _render_validation(items, findings))
    write_markdown(coverage_md, _render_coverage(items))

    return [
        Artifact(name="items.jsonl", path=items_jsonl, kind="jsonl"),
        Artifact(name="workflows.jsonl", path=workflows_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
    ]


def _render_index(items: list[WorkflowItem], infos: list[WorkflowInfo]) -> str:
    lines = ["# GitHub Actions Inventory", ""]
    lines.append(f"- Workflows: {len(infos)}")
    lines.append(f"- Steps: {len(items)}")
    actions = sum(1 for i in items if i.kind == "uses")
    pinned = sum(1 for i in items if i.kind == "uses" and i.action_pinned)
    lines.append(f"- Action uses: {actions} ({pinned} pinned to SHA)")
    lines.append("")
    if infos:
        lines.append("| Workflow | Triggers | Jobs |")
        lines.append("|---|---|---:|")
        for w in infos:
            lines.append(f"| `{w.workflow}` | {', '.join(w.triggers)} | {len(w.jobs)} |")
    return "\n".join(lines) + "\n"


def _render_validation(items: list[WorkflowItem], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Steps: {len(items)}")
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


def _render_coverage(items: list[WorkflowItem]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Steps: {len(items)}")
    if not items:
        return "\n".join(lines) + "\n"
    uses = [i for i in items if i.kind == "uses"]
    action_dist = Counter(i.action.split("@")[0] for i in uses)
    lines.append(f"- Action uses: {len(uses)}")
    lines.append(f"- Run steps: {sum(1 for i in items if i.kind == 'run')}")
    lines.append("")
    lines.append("## Actions used")
    lines.append("")
    for a, n in action_dist.most_common():
        lines.append(f"- `{a}`: {n}")
    return "\n".join(lines) + "\n"
