from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_dockerfile.loader import load_dockerfile_records
from tessera_dockerfile.schema import Instruction
from tessera_dockerfile.validator import validate_dockerfile_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[Instruction]:
    return load_dockerfile_records(input_path, options)


def validate_records(instrs: list[Instruction], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_dockerfile_records(instrs, options)


def write_artifacts(instrs: list[Instruction], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(instrs, options)

    instr_jsonl = ctx.output_dir / "instructions.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"

    write_jsonl(instr_jsonl, [i.model_dump() for i in instrs])
    write_markdown(index_md, _render_index(instrs, options))
    write_markdown(validation_md, _render_validation(instrs, findings))
    write_markdown(coverage_md, _render_coverage(instrs))

    return [
        Artifact(name="instructions.jsonl", path=instr_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
    ]


def _render_index(instrs: list[Instruction], options: dict[str, Any]) -> str:
    lines = ["# Dockerfile Inventory", ""]
    lines.append(f"- Dockerfiles: {options.get('_file_count', 0)}")
    lines.append(f"- Instructions: {len(instrs)}")
    stages = sorted({i.stage for i in instrs if i.stage})
    lines.append(f"- Build stages: {', '.join(stages) if stages else '(none named)'}")
    lines.append("")
    if not instrs:
        lines.append("_No Dockerfile instructions found._")
        return "\n".join(lines) + "\n"
    lines.append("| Instruction | Argument | Location |")
    lines.append("|---|---|---|")
    for i in instrs[:400]:
        arg = (i.argument[:70] + "…") if len(i.argument) > 70 else i.argument
        lines.append(f"| {i.instruction} | {arg} | `{i.file}:{i.lineno}` |")
    return "\n".join(lines) + "\n"


def _render_validation(instrs: list[Instruction], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Instructions: {len(instrs)}")
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


def _render_coverage(instrs: list[Instruction]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Instructions: {len(instrs)}")
    if not instrs:
        return "\n".join(lines) + "\n"
    dist = Counter(i.instruction for i in instrs)
    lines.append("")
    lines.append("## Instruction frequency")
    lines.append("")
    for instr, n in dist.most_common():
        lines.append(f"- `{instr}`: {n}")
    return "\n".join(lines) + "\n"
