from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_prompts.loader import discover_prompt_files, parse_prompt_file
from tessera_prompts.schema import PromptCase
from tessera_prompts.validator import validate_prompts


def load_prompt_records(input_path: Path, options: dict[str, Any]) -> list[PromptCase]:
    """Discover and parse prompt files into PromptCase objects."""
    files = discover_prompt_files(input_path)
    cases: list[PromptCase] = []
    parse_errors: list[dict[str, str]] = []
    for path in files:
        try:
            cases.append(parse_prompt_file(path))
        except (ValueError, Exception) as exc:
            parse_errors.append({"path": str(path), "error": str(exc)})

    options["_parse_errors"] = parse_errors
    options["_input_path"] = str(input_path)
    return cases


def validate_prompt_records(
    cases: list[PromptCase],
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
                metadata={"source_file": err["path"]},
            )
        )
    findings.extend(validate_prompts(cases))
    return findings


def write_prompt_artifacts(
    cases: list[PromptCase],
    ctx: RunContext,
    options: dict[str, Any],
) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = (
        ctx.metadata.get("findings") or validate_prompt_records(cases, options)
    )

    index_jsonl = ctx.output_dir / "index.jsonl"
    index_md = ctx.output_dir / "index.md"
    examples_jsonl = ctx.output_dir / "examples.jsonl"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"

    write_jsonl(index_jsonl, [c.model_dump() for c in cases])
    write_jsonl(examples_jsonl, _examples_rows(cases))
    write_markdown(index_md, _render_index(cases))
    write_markdown(validation_md, _render_validation(cases, findings, options))
    write_markdown(coverage_md, _render_coverage(cases))

    return [
        Artifact(name="index.jsonl", path=index_jsonl, kind="jsonl"),
        Artifact(name="examples.jsonl", path=examples_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
    ]


def _examples_rows(cases: list[PromptCase]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        for idx, ex in enumerate(case.examples, start=1):
            rendered = _render_body(case.body, ex.input)
            rows.append(
                {
                    "id": f"{case.name}::ex_{idx}",
                    "prompt_name": case.name,
                    "prompt_version": case.version,
                    "input_variables": ex.input,
                    "rendered_prompt": rendered,
                    "expected": ex.expected,
                    "notes": ex.notes,
                }
            )
    return rows


def _render_body(body: str, variables: dict[str, Any]) -> str:
    rendered = body
    for k, v in variables.items():
        rendered = rendered.replace(f"{{{{{k}}}}}", str(v))
        rendered = rendered.replace(f"{{{{ {k} }}}}", str(v))
    return rendered


def _render_index(cases: list[PromptCase]) -> str:
    lines: list[str] = ["# Prompt Catalog", ""]
    lines.append(f"- Total prompts: {len(cases)}")
    lines.append("")
    if not cases:
        lines.append("_No prompts found._")
        return "\n".join(lines) + "\n"

    lines.append("| Name | Version | Lang | Tags | Variables | Examples | Source |")
    lines.append("|---|---|---|---|---:|---:|---|")
    for case in sorted(cases, key=lambda c: (c.name, c.version)):
        tags = ", ".join(case.tags) if case.tags else ""
        source = case.metadata.get("source_file", "")
        lines.append(
            f"| `{case.name}` | {case.version} | {case.lang} | {tags} "
            f"| {len(case.variables)} | {len(case.examples)} | `{source}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_validation(
    cases: list[PromptCase],
    findings: list[ValidationFinding],
    options: dict[str, Any],
) -> str:
    lines: list[str] = ["# Validation Report", ""]
    lines.append(f"- Total prompts: {len(cases)}")
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
        lines.append("")
    return "\n".join(lines)


def _render_coverage(cases: list[PromptCase]) -> str:
    lines: list[str] = ["# Coverage Report", ""]
    lines.append(f"- Total prompts: {len(cases)}")
    if not cases:
        return "\n".join(lines) + "\n"

    with_vars = sum(1 for c in cases if c.variables)
    with_examples = sum(1 for c in cases if c.examples)
    with_hints = sum(1 for c in cases if c.model_hints)
    lines.append(f"- With declared variables: {with_vars}")
    lines.append(f"- With inline examples: {with_examples}")
    lines.append(f"- With model hints: {with_hints}")
    lines.append("")

    lang_dist = Counter(c.lang for c in cases)
    lines.append("## Languages")
    lines.append("")
    for lang, count in sorted(lang_dist.items()):
        lines.append(f"- `{lang}`: {count}")
    lines.append("")

    tag_dist: Counter[str] = Counter()
    for c in cases:
        for t in c.tags:
            tag_dist[t] += 1
    lines.append("## Tags")
    lines.append("")
    if tag_dist:
        for tag, count in tag_dist.most_common():
            lines.append(f"- `{tag}`: {count}")
    else:
        lines.append("_No tags._")
    lines.append("")
    return "\n".join(lines)
