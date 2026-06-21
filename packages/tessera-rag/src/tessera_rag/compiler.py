from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_rag.loader import load_rag_records
from tessera_rag.schema import RagCase, RagDocument
from tessera_rag.validator import validate_rag_records


def load_records(input_path: Path, options: dict[str, Any]) -> list[RagCase]:
    return load_rag_records(input_path, options)


def validate_records(cases: list[RagCase], options: dict[str, Any]) -> list[ValidationFinding]:
    return validate_rag_records(cases, options)


def write_artifacts(cases: list[RagCase], ctx: RunContext, options: dict[str, Any]) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    docs: list[RagDocument] = options.get("_docs", [])
    findings: list[ValidationFinding] = ctx.metadata.get("findings") or validate_records(cases, options)

    dataset = ctx.output_dir / "dataset.jsonl"
    corpus_index = ctx.output_dir / "corpus_index.jsonl"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    targets_md = ctx.output_dir / "retrieval_targets.md"

    write_jsonl(dataset, [c.model_dump() for c in cases])
    write_jsonl(corpus_index, [d.model_dump() for d in docs])
    write_markdown(validation_md, _render_validation(cases, docs, findings, options))
    write_markdown(coverage_md, _render_coverage(cases, docs))
    write_markdown(targets_md, _render_targets(cases, docs))

    return [
        Artifact(name="dataset.jsonl", path=dataset, kind="jsonl"),
        Artifact(name="corpus_index.jsonl", path=corpus_index, kind="jsonl"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="retrieval_targets.md", path=targets_md, kind="markdown"),
    ]


def _render_validation(cases, docs, findings: list[ValidationFinding], options) -> str:
    lines = ["# Validation Report", ""]
    lines.append(f"- Queries: {len(cases)}")
    lines.append(f"- Documents: {len(docs)}")
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
            ident = f.metadata.get("id") or f.metadata.get("doc_id") or "" if f.metadata else ""
            who = f" `{ident}`" if ident else ""
            field_part = f" [{f.field}]" if f.field else ""
            lines.append(f"- **{f.severity.upper()}** `{f.code}`{who}{field_part}: {f.message}")
        if len(findings) > 200:
            lines.append(f"- ... {len(findings) - 200} more findings omitted")
    return "\n".join(lines)


def _render_coverage(cases: list[RagCase], docs: list[RagDocument]) -> str:
    lines = ["# Coverage Report", ""]
    lines.append(f"- Queries: {len(cases)}")
    lines.append(f"- Documents: {len(docs)}")
    if not cases:
        return "\n".join(lines) + "\n"

    with_answer = sum(1 for c in cases if c.expected_answer)
    with_targets = sum(1 for c in cases if c.relevant_doc_ids)
    total_targets = sum(len(c.relevant_doc_ids) for c in cases)
    referenced = {d for c in cases for d in c.relevant_doc_ids}
    orphan = sum(1 for d in docs if d.id not in referenced)
    avg_targets = total_targets / len(cases)

    lines.append(f"- Queries with expected answer: {with_answer}")
    lines.append(f"- Queries with retrieval targets: {with_targets}")
    lines.append(f"- Average relevant docs per query: {avg_targets:.2f}")
    lines.append(f"- Documents referenced by >=1 query: {len(referenced & {d.id for d in docs})}")
    lines.append(f"- Orphan documents: {orphan}")
    lines.append("")

    tag_dist: Counter[str] = Counter()
    for c in cases:
        for t in c.tags:
            tag_dist[t] += 1
    lines.append("## Query tags")
    lines.append("")
    if tag_dist:
        for tag, count in tag_dist.most_common():
            lines.append(f"- `{tag}`: {count}")
    else:
        lines.append("_No tags._")
    return "\n".join(lines) + "\n"


def _render_targets(cases: list[RagCase], docs: list[RagDocument]) -> str:
    titles = {d.id: d.title for d in docs}
    lines = ["# Retrieval Targets", ""]
    lines.append("The gold document set each query should retrieve. A retriever "
                 "evaluated on this dataset is scored against these targets.")
    lines.append("")
    if not cases:
        lines.append("_No queries._")
        return "\n".join(lines) + "\n"

    lines.append("| Query | Targets | Has answer |")
    lines.append("|---|---|:--:|")
    for c in cases:
        if c.relevant_doc_ids:
            tgt = ", ".join(f"`{d}`" + (f" ({titles[d]})" if d in titles else " (MISSING)") for d in c.relevant_doc_ids)
        else:
            tgt = "(none)"
        has = "yes" if c.expected_answer else "no"
        lines.append(f"| `{c.id}` | {tgt} | {has} |")
    return "\n".join(lines) + "\n"
