from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_deps.loader import load_deps_records
from tessera_deps.schema import Dependency
from tessera_deps.validator import validate_deps_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[Dependency]:
    return load_deps_records(input_path, options)


def validate_records(deps: list[Dependency], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_deps_records(deps, options)


def write_artifacts(deps: list[Dependency], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(deps, options)

    deps_jsonl = ctx.output_dir / "dependencies.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    duplicates_md = ctx.output_dir / "duplicates.md"

    write_jsonl(deps_jsonl, [d.model_dump() for d in deps])
    write_markdown(index_md, _render_index(deps, options))
    write_markdown(validation_md, _render_validation(deps, findings))
    write_markdown(coverage_md, _render_coverage(deps))
    write_markdown(duplicates_md, _render_duplicates(deps))

    return [
        Artifact(name="dependencies.jsonl", path=deps_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="duplicates.md", path=duplicates_md, kind="markdown"),
    ]


def _render_index(deps: list[Dependency], options: dict[str, Any]) -> str:
    lines = ["# Dependency Inventory", ""]
    lines.append(f"- Manifests: {len(options.get('_manifests', []))}")
    lines.append(f"- Dependencies: {len(deps)}")
    pinned = sum(1 for d in deps if d.pinning == "pinned")
    if deps:
        lines.append(f"- Pinned: {pinned} ({100*pinned/len(deps):.0f}%)")
    lines.append("")
    if not deps:
        lines.append("_No dependencies found._")
        return "\n".join(lines) + "\n"
    lines.append("| Name | Ecosystem | Scope | Constraint | Pinning | Source |")
    lines.append("|---|---|---|---|---|---|")
    for d in sorted(deps, key=lambda x: (x.ecosystem, x.name)):
        lines.append(f"| `{d.name}` | {d.ecosystem} | {d.scope} | {d.constraint or '-'} | {d.pinning} | `{d.source_file}` |")
    return "\n".join(lines) + "\n"


def _render_validation(deps: list[Dependency], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Dependencies: {len(deps)}")
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


def _render_coverage(deps: list[Dependency]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Dependencies: {len(deps)}")
    if not deps:
        return "\n".join(lines) + "\n"
    by_eco = Counter(d.ecosystem for d in deps)
    by_scope = Counter(d.scope for d in deps)
    by_pinning = Counter(d.pinning for d in deps)
    lines.append("")
    lines.append("## By pinning")
    lines.append("")
    for k in ("pinned", "ranged", "unpinned"):
        if by_pinning.get(k):
            lines.append(f"- {k}: {by_pinning[k]}")
    lines.append("")
    lines.append("## By ecosystem")
    lines.append("")
    for k, n in by_eco.most_common():
        lines.append(f"- `{k}`: {n}")
    lines.append("")
    lines.append("## By scope")
    lines.append("")
    for k, n in by_scope.most_common():
        lines.append(f"- {k}: {n}")
    return "\n".join(lines) + "\n"


def _render_duplicates(deps: list[Dependency]) -> str:
    by_key: dict[tuple[str, str], list[Dependency]] = defaultdict(list)
    for d in deps:
        by_key[(d.ecosystem, d.name)].append(d)
    dups = {k: v for k, v in by_key.items() if len({d.source_file for d in v}) > 1}

    lines = ["# Duplicate Dependencies", ""]
    lines.append("Dependencies declared in more than one manifest.")
    lines.append("")
    if not dups:
        lines.append("_No duplicates across manifests._")
        return "\n".join(lines) + "\n"
    for (eco, name), group in sorted(dups.items()):
        lines.append(f"## `{name}` ({eco})")
        lines.append("")
        for d in group:
            lines.append(f"- `{d.source_file}` ({d.scope}): `{d.constraint or 'unpinned'}`")
        lines.append("")
    return "\n".join(lines)
