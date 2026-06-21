from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding
from tessera_core.workspace import write_json

from tessera_repo.loader import load_repo_records
from tessera_repo.schema import RepoFile, RepoManifest, RepoMap
from tessera_repo.validator import validate_repo_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[RepoFile]:
    return load_repo_records(input_path, options)


def validate_records(files: list[RepoFile], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_repo_records(files, options)


def write_artifacts(files: list[RepoFile], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    repo_map: RepoMap = options["_map"]
    manifests: list[RepoManifest] = options.get("_manifests", [])
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(files, options)

    files_jsonl = ctx.output_dir / "files.jsonl"
    map_json = ctx.output_dir / "repo_map.json"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    deps_md = ctx.output_dir / "dependencies_report.md"

    write_jsonl(files_jsonl, [f.model_dump() for f in files])
    write_json(map_json, repo_map.model_dump())
    write_markdown(index_md, _render_index(repo_map))
    write_markdown(validation_md, _render_validation(files, findings))
    write_markdown(coverage_md, _render_coverage(files, repo_map))
    write_markdown(deps_md, _render_deps(manifests))

    return [
        Artifact(name="files.jsonl", path=files_jsonl, kind="jsonl"),
        Artifact(name="repo_map.json", path=map_json, kind="json"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="dependencies_report.md", path=deps_md, kind="markdown"),
    ]


def _render_index(m: RepoMap) -> str:
    lines = ["# Repository Map", ""]
    lines.append(f"- Root: `{m.root}`")
    lines.append(f"- Files: {m.file_count}")
    lines.append(f"- Lines of code: {m.total_loc}")
    lines.append(f"- Size: {m.total_bytes / 1024:.1f} KB")
    lines.append("")

    lines.append("## Signals")
    lines.append("")
    for key in ("has_readme", "has_license", "has_tests", "has_ci", "has_gitignore"):
        mark = "yes" if m.signals.get(key) else "NO"
        lines.append(f"- {key.replace('has_', '')}: {mark}")
    lines.append("")

    lines.append("## Languages")
    lines.append("")
    if m.languages:
        lines.append("| Language | Files |")
        lines.append("|---|---:|")
        for lang, count in m.languages.items():
            lines.append(f"| {lang} | {count} |")
    else:
        lines.append("_None detected._")
    lines.append("")

    lines.append("## Top-level layout")
    lines.append("")
    lines.append("| Path | Files |")
    lines.append("|---|---:|")
    for d, count in m.top_dirs.items():
        lines.append(f"| `{d}` | {count} |")
    lines.append("")

    if m.manifests:
        lines.append("## Dependency manifests")
        lines.append("")
        for man in m.manifests:
            lines.append(f"- `{man.path}` ({man.kind}): {len(man.dependencies)} dependencies")
    return "\n".join(lines) + "\n"


def _render_validation(files: list[RepoFile], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Files: {len(files)}")
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
            field_part = f" [{f.field}]" if f.field else ""
            lines.append(f"- **{f.severity.upper()}** `{f.code}`{field_part}: {f.message}")
    return "\n".join(lines)


def _render_coverage(files: list[RepoFile], m: RepoMap) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Files: {len(files)}")
    source = m.by_kind.get("source", 0)
    test = m.by_kind.get("test", 0)
    ratio = (test / source) if source else 0.0
    lines.append(f"- Source files: {source}")
    lines.append(f"- Test files: {test}")
    lines.append(f"- Test-to-source ratio: {ratio:.2f}")
    lines.append("")
    lines.append("## Files by kind")
    lines.append("")
    lines.append("| Kind | Files |")
    lines.append("|---|---:|")
    for kind, count in m.by_kind.items():
        lines.append(f"| {kind} | {count} |")
    return "\n".join(lines) + "\n"


def _render_deps(manifests: list[RepoManifest]) -> str:
    lines = ["# Dependencies Report", ""]
    total = sum(len(man.dependencies) for man in manifests)
    lines.append(f"- Manifests: {len(manifests)}")
    lines.append(f"- Total declared dependencies: {total}")
    lines.append("")
    if not manifests:
        lines.append("_No dependency manifests found._")
        return "\n".join(lines) + "\n"
    for man in manifests:
        lines.append(f"## `{man.path}` ({man.kind})")
        lines.append("")
        if man.dependencies:
            for dep in man.dependencies:
                lines.append(f"- `{dep}`")
        else:
            lines.append("_No dependencies parsed._")
        lines.append("")
    return "\n".join(lines)
