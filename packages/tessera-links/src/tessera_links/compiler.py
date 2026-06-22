from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_links.loader import load_link_records
from tessera_links.schema import Link
from tessera_links.validator import validate_link_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[Link]:
    return load_link_records(input_path, options)


def validate_records(links: list[Link], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_link_records(links, options)


def write_artifacts(links: list[Link], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(links, options)

    links_jsonl = ctx.output_dir / "links.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    broken_md = ctx.output_dir / "broken.md"

    write_jsonl(links_jsonl, [link.model_dump() for link in links])
    write_markdown(index_md, _render_index(links, options))
    write_markdown(validation_md, _render_validation(links, findings))
    write_markdown(coverage_md, _render_coverage(links, options))
    write_markdown(broken_md, _render_broken(links, options))

    return [
        Artifact(name="links.jsonl", path=links_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="broken.md", path=broken_md, kind="markdown"),
    ]


def _render_index(links: list[Link], options: dict[str, Any]) -> str:
    lines = ["# Link Inventory", ""]
    lines.append(f"- Markdown files: {options.get('_md_count', 0)}")
    lines.append(f"- Links: {len(links)}")
    broken = sum(1 for link in links if link.broken)
    lines.append(f"- Broken: {broken}")
    lines.append(f"- Orphan docs: {len(options.get('_orphans', []))}")
    lines.append("")
    if not links:
        lines.append("_No links found._")
        return "\n".join(lines) + "\n"
    lines.append("| Source | Kind | Href | Broken |")
    lines.append("|---|---|---|:--:|")
    for link in links[:500]:
        lines.append(f"| `{link.source_file}:{link.lineno}` | {link.kind} | {link.href} | {'yes' if link.broken else '-'} |")
    return "\n".join(lines) + "\n"


def _render_validation(links: list[Link], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Links: {len(links)}")
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


def _render_coverage(links: list[Link], options: dict[str, Any]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Links: {len(links)}")
    if not links:
        return "\n".join(lines) + "\n"
    by_kind = Counter(link.kind for link in links)
    lines.append("")
    lines.append("## By kind")
    lines.append("")
    for kind, n in by_kind.most_common():
        lines.append(f"- `{kind}`: {n}")
    lines.append("")
    lines.append("Note: external links are inventoried but not fetched (no network).")
    return "\n".join(lines) + "\n"


def _render_broken(links: list[Link], options: dict[str, Any]) -> str:
    broken = [link for link in links if link.broken]
    lines = ["# Broken Links", ""]
    lines.append(f"- Broken links: {len(broken)}")
    lines.append(f"- Orphan docs: {len(options.get('_orphans', []))}")
    lines.append("")
    if broken:
        lines.append("## Broken")
        lines.append("")
        for link in broken:
            lines.append(f"- `{link.source_file}:{link.lineno}` → `{link.href}` — {link.reason}")
        lines.append("")
    else:
        lines.append("_No broken links._")
        lines.append("")
    orphans = options.get("_orphans", [])
    if orphans:
        lines.append("## Orphan docs (linked from nowhere)")
        lines.append("")
        for o in orphans:
            lines.append(f"- `{o}`")
    return "\n".join(lines) + "\n"
