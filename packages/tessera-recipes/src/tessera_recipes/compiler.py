from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from tessera_core.artifacts import write_jsonl, write_markdown
from tessera_core.models import Artifact, RunContext, ValidationFinding

from tessera_recipes.graph import analyze
from tessera_recipes.loader import discover_recipe_files, parse_recipe_file
from tessera_recipes.schema import Recipe
from tessera_recipes.validator import validate_recipes


def load_recipe_records(input_path: Path, options: dict[str, Any]) -> list[Recipe]:
    files = discover_recipe_files(input_path)
    recipes: list[Recipe] = []
    parse_errors: list[dict[str, str]] = []
    for path in files:
        try:
            recipes.append(parse_recipe_file(path))
        except (ValueError, Exception) as exc:
            parse_errors.append({"path": str(path), "error": str(exc)})

    options["_parse_errors"] = parse_errors
    options["_input_path"] = str(input_path)
    return recipes


def validate_recipe_records(
    recipes: list[Recipe],
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
    findings.extend(validate_recipes(recipes))
    return findings


def write_recipe_artifacts(
    recipes: list[Recipe],
    ctx: RunContext,
    options: dict[str, Any],
) -> list[Artifact]:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[ValidationFinding] = (
        ctx.metadata.get("findings") or validate_recipe_records(recipes, options)
    )

    index_jsonl = ctx.output_dir / "index.jsonl"
    plans_jsonl = ctx.output_dir / "plans.jsonl"
    index_md = ctx.output_dir / "index.md"
    validation_md = ctx.output_dir / "validation_report.md"
    coverage_md = ctx.output_dir / "coverage_report.md"
    plans_md = ctx.output_dir / "execution_plans.md"

    write_jsonl(index_jsonl, [r.model_dump() for r in recipes])
    write_jsonl(plans_jsonl, _plan_rows(recipes))
    write_markdown(index_md, _render_index(recipes))
    write_markdown(validation_md, _render_validation(recipes, findings, options))
    write_markdown(coverage_md, _render_coverage(recipes))
    write_markdown(plans_md, _render_plans(recipes))

    return [
        Artifact(name="index.jsonl", path=index_jsonl, kind="jsonl"),
        Artifact(name="plans.jsonl", path=plans_jsonl, kind="jsonl"),
        Artifact(name="index.md", path=index_md, kind="markdown"),
        Artifact(name="validation_report.md", path=validation_md, kind="markdown"),
        Artifact(name="coverage_report.md", path=coverage_md, kind="markdown"),
        Artifact(name="execution_plans.md", path=plans_md, kind="markdown"),
    ]


def _plan_rows(recipes: list[Recipe]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in recipes:
        result = analyze(r)
        rows.append(
            {
                "recipe": r.name,
                "version": r.version,
                "acyclic": result.is_acyclic,
                "execution_order": result.order,
                "edges": result.edges,
                "cycle": result.cycle,
                "step_count": len(r.steps),
            }
        )
    return rows


def _render_index(recipes: list[Recipe]) -> str:
    lines: list[str] = ["# Recipe Catalog", ""]
    lines.append(f"- Total recipes: {len(recipes)}")
    lines.append("")
    if not recipes:
        lines.append("_No recipes found._")
        return "\n".join(lines) + "\n"

    lines.append("| Name | Version | Tags | Inputs | Steps | Outputs | Acyclic | Source |")
    lines.append("|---|---|---|---:|---:|---:|:--:|---|")
    for r in sorted(recipes, key=lambda x: (x.name, x.version)):
        tags = ", ".join(r.tags) if r.tags else ""
        src = r.metadata.get("source_file", "")
        acyclic = "yes" if analyze(r).is_acyclic else "NO"
        lines.append(
            f"| `{r.name}` | {r.version} | {tags} | {len(r.inputs)} "
            f"| {len(r.steps)} | {len(r.outputs)} | {acyclic} | `{src}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_validation(
    recipes: list[Recipe],
    findings: list[ValidationFinding],
    options: dict[str, Any],
) -> str:
    lines: list[str] = ["# Validation Report", ""]
    lines.append(f"- Total recipes: {len(recipes)}")
    lines.append(f"- Findings: {len(findings)}")
    lines.append(f"- Parse errors: {len(options.get('_parse_errors', []))}")
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


def _render_coverage(recipes: list[Recipe]) -> str:
    lines: list[str] = ["# Coverage Report", ""]
    lines.append(f"- Total recipes: {len(recipes)}")
    if not recipes:
        return "\n".join(lines) + "\n"

    total_steps = sum(len(r.steps) for r in recipes)
    with_inputs = sum(1 for r in recipes if r.inputs)
    with_outputs = sum(1 for r in recipes if r.outputs)
    acyclic = sum(1 for r in recipes if analyze(r).is_acyclic)
    avg_steps = total_steps / len(recipes)

    lines.append(f"- Total steps across recipes: {total_steps}")
    lines.append(f"- Average steps per recipe: {avg_steps:.1f}")
    lines.append(f"- Recipes with declared inputs: {with_inputs}")
    lines.append(f"- Recipes with declared outputs: {with_outputs}")
    lines.append(f"- Acyclic recipes: {acyclic} / {len(recipes)}")
    lines.append("")

    tag_dist: Counter[str] = Counter()
    for r in recipes:
        for t in r.tags:
            tag_dist[t] += 1
    lines.append("## Tags")
    lines.append("")
    if tag_dist:
        for tag, count in tag_dist.most_common():
            lines.append(f"- `{tag}`: {count}")
    else:
        lines.append("_No tags._")
    return "\n".join(lines) + "\n"


def _render_plans(recipes: list[Recipe]) -> str:
    lines: list[str] = ["# Execution Plans", ""]
    if not recipes:
        lines.append("_No recipes found._")
        return "\n".join(lines) + "\n"

    for r in sorted(recipes, key=lambda x: x.name):
        result = analyze(r)
        lines.append(f"## `{r.name}` v{r.version}")
        lines.append("")
        if not result.is_acyclic:
            lines.append(f"**Cyclic — cannot order.** Cycle: `{' -> '.join(result.cycle)}`")
            lines.append("")
            continue

        lines.append("Topological execution order:")
        lines.append("")
        for i, step_id in enumerate(result.order, start=1):
            deps = result.edges.get(step_id, [])
            dep_str = f" (after {', '.join(f'`{d}`' for d in deps)})" if deps else ""
            lines.append(f"{i}. `{step_id}`{dep_str}")
        lines.append("")

        lines.append("Dependency edges:")
        lines.append("")
        lines.append("```text")
        for step_id in result.order:
            deps = result.edges.get(step_id, [])
            if deps:
                for d in deps:
                    lines.append(f"{d} -> {step_id}")
            else:
                lines.append(f"(root) -> {step_id}")
        lines.append("```")
        lines.append("")
    return "\n".join(lines)
