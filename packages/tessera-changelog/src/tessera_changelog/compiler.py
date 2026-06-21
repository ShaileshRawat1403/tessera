from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_changelog.loader import load_changelog_records
from tessera_changelog.render import render_changelog, render_release_notes
from tessera_changelog.schema import Commit
from tessera_changelog.validator import validate_changelog_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[Commit]:
    return load_changelog_records(input_path, options)


def validate_records(commits: list[Commit], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_changelog_records(commits, options)


def write_artifacts(commits: list[Commit], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(commits, options)

    commits_jsonl = ctx.output_dir / "commits.jsonl"
    changelog_md = ctx.output_dir / "CHANGELOG.md"
    release_md = ctx.output_dir / "release_notes.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"

    write_jsonl(commits_jsonl, [c.model_dump() for c in commits])
    write_markdown(changelog_md, render_changelog(commits))
    write_markdown(release_md, render_release_notes(commits))
    write_markdown(validation_md, _render_validation(commits, findings, options))
    write_markdown(coverage_md, _render_coverage(commits))

    return [
        Artifact(name="commits.jsonl", path=commits_jsonl, kind="jsonl"),
        Artifact(name="CHANGELOG.md", path=changelog_md, kind="markdown"),
        Artifact(name="release_notes.md", path=release_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
    ]


def _render_validation(commits: list[Commit], findings: list[ValidationFinding], options: dict) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Commits: {len(commits)}")
    lines.append(f"- Source: {options.get('_source', 'unknown')}")
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
            h = f.metadata.get("hash", "") if f.metadata else ""
            who = f" `{h}`" if h else ""
            lines.append(f"- **{f.severity.upper()}** `{f.code}`{who}: {f.message}")
        if len(findings) > 200:
            lines.append(f"- ... {len(findings) - 200} more findings omitted")
    return "\n".join(lines)


def _render_coverage(commits: list[Commit]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Commits: {len(commits)}")
    if not commits:
        return "\n".join(lines) + "\n"

    conventional = sum(1 for c in commits if c.conventional)
    pct = 100 * conventional / len(commits)
    lines.append(f"- Conventional commits: {conventional} ({pct:.0f}%)")
    lines.append(f"- Breaking changes: {sum(1 for c in commits if c.breaking)}")
    lines.append("")

    type_dist = Counter(c.type for c in commits)
    lines.append("## Commit types")
    lines.append("")
    for t, n in type_dist.most_common():
        lines.append(f"- `{t}`: {n}")
    lines.append("")

    author_dist = Counter(c.author for c in commits if c.author)
    lines.append("## Authors")
    lines.append("")
    for a, n in author_dist.most_common(10):
        lines.append(f"- {a}: {n}")
    return "\n".join(lines) + "\n"
