from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_glossary.loader import load_glossary_records
from tessera_glossary.schema import Term
from tessera_glossary.validator import validate_glossary_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[Term]:
    return load_glossary_records(input_path, options)


def validate_records(terms: list[Term], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_glossary_records(terms, options)


def write_artifacts(terms: list[Term], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(terms, options)
    clusters = options.get("_clusters", [])

    glossary_jsonl = ctx.output_dir / "glossary.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    inconsistencies_md = ctx.output_dir / "inconsistencies.md"

    write_jsonl(glossary_jsonl, [t.model_dump() for t in terms])
    write_markdown(index_md, _render_index(terms, options))
    write_markdown(validation_md, _render_validation(terms, findings))
    write_markdown(coverage_md, _render_coverage(terms, options))
    write_markdown(inconsistencies_md, _render_inconsistencies(clusters))

    return [
        Artifact(name="glossary.jsonl", path=glossary_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="inconsistencies.md", path=inconsistencies_md, kind="markdown"),
    ]


def _render_index(terms: list[Term], options: dict[str, Any]) -> str:
    lines = ["# Project Glossary", ""]
    lines.append(f"- Distinct terms: {len(terms)}")
    lines.append(f"- Code files scanned: {options.get('_code_files', 0)}")
    lines.append(f"- Doc files scanned: {options.get('_doc_files', 0)}")
    lines.append("")
    lines.append("The most frequent domain words across code and docs — your project's")
    lines.append("ubiquitous language.")
    lines.append("")
    if not terms:
        lines.append("_No vocabulary extracted._")
        return "\n".join(lines) + "\n"
    lines.append("| Term | Count | In code | In docs |")
    lines.append("|---|---:|:--:|:--:|")
    for t in terms[:60]:
        lines.append(f"| `{t.term}` | {t.count} | {'yes' if t.in_code else '-'} | {'yes' if t.in_docs else '-'} |")
    return "\n".join(lines) + "\n"


def _render_validation(terms: list[Term], findings: list[ValidationFinding]) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Terms: {len(terms)}")
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
            lines.append(f"- **{f.severity.upper()}** `{f.code}`: {f.message}")
    return "\n".join(lines)


def _render_coverage(terms: list[Term], options: dict[str, Any]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Distinct terms: {len(terms)}")
    if not terms:
        return "\n".join(lines) + "\n"
    code_only = sum(1 for t in terms if t.in_code and not t.in_docs)
    doc_only = sum(1 for t in terms if t.in_docs and not t.in_code)
    both = sum(1 for t in terms if t.in_code and t.in_docs)
    lines.append(f"- Code-only terms: {code_only}")
    lines.append(f"- Doc-only terms: {doc_only}")
    lines.append(f"- Shared (code + docs): {both}")
    lines.append("")
    lines.append("Terms in code but never in docs may be undocumented domain concepts;")
    lines.append("terms in docs but never in code may be aspirational or stale.")
    return "\n".join(lines) + "\n"


def _render_inconsistencies(clusters: list[dict[str, Any]]) -> str:
    lines = ["# Terminology Inconsistencies", ""]
    lines.append("Concepts written more than one way across the codebase. Standardizing")
    lines.append("on a single spelling makes the code searchable and the vocabulary clear.")
    lines.append("")
    if not clusters:
        lines.append("_No terminology inconsistencies detected._")
        return "\n".join(lines) + "\n"
    for c in clusters:
        forms = ", ".join(f"`{k}` ({v})" for k, v in c["forms"].items())
        lines.append(f"## concept: {c['concept']}")
        lines.append("")
        lines.append(f"- Forms in use: {forms}")
        lines.append(f"- Recommended: `{c['recommended']}` (most frequent)")
        lines.append("")
    return "\n".join(lines)
