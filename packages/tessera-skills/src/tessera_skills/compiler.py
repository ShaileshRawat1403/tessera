from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_skills.loader import discover_skill_folders, parse_skill_folder
from tessera_skills.overlap import find_overlaps
from tessera_skills.schema import SkillManifest
from tessera_skills.validator import validate_skills


def load_skill_records(input_path: Path, options: dict[str, Any]) -> list[SkillManifest]:
    folders = discover_skill_folders(input_path)
    skills: list[SkillManifest] = []
    parse_errors: list[dict[str, str]] = []
    for folder in folders:
        try:
            skills.append(parse_skill_folder(folder))
        except (ValueError, Exception) as exc:
            parse_errors.append({"path": str(folder), "error": str(exc)})

    options["_parse_errors"] = parse_errors
    options["_input_path"] = str(input_path)
    return skills


def validate_skill_records(
    skills: list[SkillManifest],
    options: dict[str, Any],
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for err in options.get("_parse_errors", []):
        findings.append(
            ValidationFinding(
                severity="error",
                code="parse_error",
                message=f"failed to parse: {err['error']}",
                field=None,
                metadata={"source_folder": err["path"]},
            )
        )
    findings.extend(validate_skills(skills))
    return findings


def write_skill_artifacts(
    skills: list[SkillManifest],
    ctx: RunContext,
    options: dict[str, Any],
) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = (
        ctx.metadata.get("findings") or validate_skill_records(skills, options)
    )

    index_jsonl = ctx.output_dir / "index.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    deps_md = ctx.output_dir / "dependencies_report.md"

    write_jsonl(index_jsonl, [s.model_dump() for s in skills])
    write_markdown(index_md, _render_index(skills))
    write_markdown(validation_md, _render_validation(skills, findings, options))
    write_markdown(coverage_md, _render_coverage(skills))
    write_markdown(deps_md, _render_dependencies(skills))

    return [
        Artifact(name="index.jsonl", path=index_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="dependencies_report.md", path=deps_md, kind="markdown"),
    ]


def _render_index(skills: list[SkillManifest]) -> str:
    lines: list[str] = ["# Skill Catalog", ""]
    lines.append(f"- Total skills: {len(skills)}")
    lines.append("")
    if not skills:
        lines.append("_No skills found._")
        return "\n".join(lines) + "\n"

    lines.append("| Name | Version | Tags | Files | Size (KB) | Bash | MCP | Source |")
    lines.append("|---|---|---|---:|---:|---:|---:|---|")
    for skill in sorted(skills, key=lambda s: s.name):
        tags = ", ".join(skill.tags) if skill.tags else ""
        source = skill.metadata.get("source_folder", "")
        size_kb = skill.total_bytes / 1024
        lines.append(
            f"| `{skill.name}` | {skill.version} | {tags} | {len(skill.files)} "
            f"| {size_kb:.1f} | {len(skill.dependencies.bash_commands)} "
            f"| {len(skill.dependencies.mcp_tools)} | `{source}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_validation(
    skills: list[SkillManifest],
    findings: list[ValidationFinding],
    options: dict[str, Any],
) -> str:
    lines: list[str] = ["# Validation Report", ""]
    lines.append(f"- Total skills: {len(skills)}")
    lines.append(f"- Findings: {len(findings)}")
    parse_errors = options.get("_parse_errors", [])
    lines.append(f"- Parse errors: {len(parse_errors)}")
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
            name = f.metadata.get("name", "") if f.metadata else ""
            who = f" `{name}`" if name else ""
            field_part = f" [{f.field}]" if f.field else ""
            lines.append(f"- **{f.severity.upper()}** `{f.code}`{who}{field_part}: {f.message}")
        if len(findings) > 200:
            lines.append(f"- ... {len(findings) - 200} more findings omitted")
    return "\n".join(lines)


def _render_coverage(skills: list[SkillManifest]) -> str:
    lines: list[str] = ["# Coverage Report", ""]
    lines.append(f"- Total skills: {len(skills)}")
    if not skills:
        return "\n".join(lines) + "\n"

    with_tags = sum(1 for s in skills if s.tags)
    with_license = sum(1 for s in skills if s.license)
    with_scripts = sum(1 for s in skills if any(f.kind == "script" for f in s.files))
    with_references = sum(1 for s in skills if any(f.kind == "reference" for f in s.files))
    with_examples = sum(1 for s in skills if any(f.kind == "example" for f in s.files))

    lines.append(f"- With tags: {with_tags}")
    lines.append(f"- With license: {with_license}")
    lines.append(f"- With scripts: {with_scripts}")
    lines.append(f"- With references: {with_references}")
    lines.append(f"- With examples: {with_examples}")
    lines.append("")

    tag_dist: Counter[str] = Counter()
    for s in skills:
        for t in s.tags:
            tag_dist[t] += 1
    lines.append("## Tags")
    lines.append("")
    if tag_dist:
        for tag, count in tag_dist.most_common():
            lines.append(f"- `{tag}`: {count}")
    else:
        lines.append("_No tags._")
    return "\n".join(lines) + "\n"


def _render_dependencies(skills: list[SkillManifest]) -> str:
    lines: list[str] = ["# Dependencies Report", ""]
    if not skills:
        lines.append("_No skills found._")
        return "\n".join(lines) + "\n"

    bash_dist: Counter[str] = Counter()
    mcp_dist: Counter[str] = Counter()
    skill_refs_dist: Counter[str] = Counter()
    for s in skills:
        bash_dist.update(s.dependencies.bash_commands)
        mcp_dist.update(s.dependencies.mcp_tools)
        skill_refs_dist.update(s.dependencies.skills)

    lines.append("## Bash command surface")
    lines.append("")
    if bash_dist:
        for cmd, count in bash_dist.most_common():
            lines.append(f"- `{cmd}` ({count})")
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## MCP tool surface")
    lines.append("")
    if mcp_dist:
        for tool, count in mcp_dist.most_common():
            lines.append(f"- `{tool}` ({count})")
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## Skill-to-skill references")
    lines.append("")
    if skill_refs_dist:
        for ref, count in skill_refs_dist.most_common():
            lines.append(f"- `/{ref}` ({count})")
    else:
        lines.append("_None._")
    lines.append("")

    overlaps = find_overlaps(skills)
    lines.append("## Description Overlap")
    lines.append("")
    if not overlaps:
        lines.append("_No overlap detected above the warning threshold._")
        return "\n".join(lines) + "\n"

    lines.append("| Skill A | Skill B | Jaccard | Severity |")
    lines.append("|---|---|---:|---|")
    for p in sorted(overlaps, key=lambda x: -x.similarity):
        lines.append(f"| `{p.name_a}` | `{p.name_b}` | {p.similarity:.2f} | {p.severity} |")
    return "\n".join(lines) + "\n"
