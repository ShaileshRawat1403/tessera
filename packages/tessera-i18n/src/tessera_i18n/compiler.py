from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_i18n.loader import load_i18n_records
from tessera_i18n.schema import LocaleFile
from tessera_i18n.validator import validate_i18n_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[LocaleFile]:
    return load_i18n_records(input_path, options)


def validate_records(locales: list[LocaleFile], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_i18n_records(locales, options)


def write_artifacts(locales: list[LocaleFile], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(locales, options)
    ref = options.get("_reference", "")

    locales_jsonl = ctx.output_dir / "locales.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    missing_md = ctx.output_dir / "missing_keys.md"

    write_jsonl(locales_jsonl, [loc.model_dump() for loc in locales])
    write_markdown(index_md, _render_index(locales, ref))
    write_markdown(validation_md, _render_validation(locales, findings))
    write_markdown(coverage_md, _render_coverage(locales, ref))
    write_markdown(missing_md, _render_missing(locales, ref))

    return [
        Artifact(name="locales.jsonl", path=locales_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="missing_keys.md", path=missing_md, kind="markdown"),
    ]


def _render_index(locales: list[LocaleFile], ref: str) -> str:
    lines = ["# i18n Coverage", ""]
    lines.append(f"- Locales: {len(locales)}")
    lines.append(f"- Reference: `{ref or '(none)'}`")
    lines.append("")
    if not locales:
        lines.append("_No locale files found._")
        return "\n".join(lines) + "\n"
    lines.append("| Locale | Keys | Coverage | Missing | Extra | Empty | Ref |")
    lines.append("|---|---:|---:|---:|---:|---:|:--:|")
    for loc in sorted(locales, key=lambda x: x.locale):
        lines.append(
            f"| `{loc.locale}` | {loc.key_count} | {loc.coverage*100:.0f}% "
            f"| {len(loc.missing_keys)} | {len(loc.extra_keys)} | {len(loc.empty_keys)} "
            f"| {'yes' if loc.is_reference else '-'} |"
        )
    return "\n".join(lines) + "\n"


def _render_validation(locales: list[LocaleFile], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Locales: {len(locales)}")
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


def _render_coverage(locales: list[LocaleFile], ref: str) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Locales: {len(locales)}")
    lines.append(f"- Reference: `{ref or '(none)'}`")
    if not locales:
        return "\n".join(lines) + "\n"
    fully = sum(1 for loc in locales if loc.coverage >= 1.0)
    lines.append(f"- Fully translated: {fully}/{len(locales)}")
    avg = sum(loc.coverage for loc in locales) / len(locales)
    lines.append(f"- Average coverage: {avg*100:.0f}%")
    return "\n".join(lines) + "\n"


def _render_missing(locales: list[LocaleFile], ref: str) -> str:
    lines = ["# Missing Keys by Locale", ""]
    lines.append(f"Keys present in the reference (`{ref}`) but missing from each locale.")
    lines.append("")
    any_missing = False
    for loc in sorted(locales, key=lambda x: x.locale):
        if loc.is_reference or not loc.missing_keys:
            continue
        any_missing = True
        lines.append(f"## `{loc.locale}` ({len(loc.missing_keys)} missing)")
        lines.append("")
        for k in loc.missing_keys[:200]:
            lines.append(f"- `{k}`")
        if len(loc.missing_keys) > 200:
            lines.append(f"- ... {len(loc.missing_keys) - 200} more")
        lines.append("")
    if not any_missing:
        lines.append("_All locales have every reference key._")
    return "\n".join(lines)
