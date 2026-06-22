from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_docs.loader import load_docs_records
from tessera_docs.schema import DocSymbol
from tessera_docs.validator import validate_docs_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[DocSymbol]:
    return load_docs_records(input_path, options)


def validate_records(symbols: list[DocSymbol], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_docs_records(symbols, options)


def write_artifacts(symbols: list[DocSymbol], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(symbols, options)

    symbols_jsonl = ctx.output_dir / "symbols.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    undocumented_md = ctx.output_dir / "undocumented.md"

    write_jsonl(symbols_jsonl, [s.model_dump() for s in symbols])
    write_markdown(index_md, _render_index(symbols, options))
    write_markdown(validation_md, _render_validation(symbols, findings))
    write_markdown(coverage_md, _render_coverage(symbols))
    write_markdown(undocumented_md, _render_undocumented(symbols))

    return [
        Artifact(name="symbols.jsonl", path=symbols_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="undocumented.md", path=undocumented_md, kind="markdown"),
    ]


def _coverage(symbols: list[DocSymbol]) -> tuple[int, int, float]:
    public = [s for s in symbols if s.is_public]
    documented = sum(1 for s in public if s.has_docstring)
    pct = (documented / len(public)) if public else 1.0
    return documented, len(public), pct


def _render_index(symbols: list[DocSymbol], options: dict[str, Any]) -> str:
    documented, total, pct = _coverage(symbols)
    lines = ["# Documentation Coverage", ""]
    lines.append(f"- Files scanned: {options.get('_file_count', 0)}")
    lines.append(f"- Public symbols: {total}")
    lines.append(f"- Documented: {documented}")
    lines.append(f"- Coverage: {pct*100:.0f}%")
    return "\n".join(lines) + "\n"


def _render_validation(symbols: list[DocSymbol], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Symbols: {len(symbols)}")
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
        if len(findings) > 300:
            lines.append(f"- ... {len(findings) - 300} more findings omitted")
    return "\n".join(lines)


def _render_coverage(symbols: list[DocSymbol]) -> str:
    lines = ["# Coverage Report", ""]
    documented, total, pct = _coverage(symbols)
    lines.append(f"- Public symbols: {total}")
    lines.append(f"- Documented: {documented} ({pct*100:.0f}%)")
    lines.append("")

    # by kind
    lines.append("## By kind")
    lines.append("")
    lines.append("| Kind | Public | Documented | Coverage |")
    lines.append("|---|---:|---:|---:|")
    by_kind: dict[str, list[DocSymbol]] = defaultdict(list)
    for s in symbols:
        if s.is_public:
            by_kind[s.kind].append(s)
    for kind in ("module", "class", "function", "method"):
        items = by_kind.get(kind, [])
        if not items:
            continue
        doc = sum(1 for s in items if s.has_docstring)
        lines.append(f"| {kind} | {len(items)} | {doc} | {100*doc/len(items):.0f}% |")
    lines.append("")

    # worst files
    by_file: dict[str, list[DocSymbol]] = defaultdict(list)
    for s in symbols:
        if s.is_public:
            by_file[s.path].append(s)
    rows = []
    for path, items in by_file.items():
        doc = sum(1 for s in items if s.has_docstring)
        rows.append((doc / len(items), path, doc, len(items)))
    rows.sort()
    lines.append("## Lowest-coverage files")
    lines.append("")
    lines.append("| File | Documented | Public | Coverage |")
    lines.append("|---|---:|---:|---:|")
    for cov, path, doc, tot in rows[:15]:
        lines.append(f"| `{path}` | {doc} | {tot} | {cov*100:.0f}% |")
    return "\n".join(lines) + "\n"


def _render_undocumented(symbols: list[DocSymbol]) -> str:
    missing = [s for s in symbols if s.is_public and not s.has_docstring]
    lines = ["# Undocumented Public Symbols", ""]
    lines.append(f"- Count: {len(missing)}")
    lines.append("")
    if not missing:
        lines.append("_Everything public is documented._")
        return "\n".join(lines) + "\n"
    lines.append("| File | Symbol | Kind | Line |")
    lines.append("|---|---|---|---:|")
    for s in sorted(missing, key=lambda x: (x.path, x.lineno)):
        lines.append(f"| `{s.path}` | `{s.qualname or s.name}` | {s.kind} | {s.lineno} |")
    return "\n".join(lines) + "\n"
