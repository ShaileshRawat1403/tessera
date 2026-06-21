from __future__ import annotations

import re
from collections import Counter

from tessera_core.models import ValidationFinding

from tessera_recipes.graph import (
    analyze,
    referenced_input_names,
    referenced_step_ids,
)
from tessera_recipes.schema import Recipe

_NAME_RE = re.compile(r"^[a-z0-9]+([_-][a-z0-9]+)*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([+-][0-9A-Za-z.-]+)?$")


def validate_recipes(recipes: list[Recipe]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for r in recipes:
        findings.extend(_validate_one(r))

    name_counts = Counter(r.name for r in recipes if r.name)
    for name, count in name_counts.items():
        if count > 1:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="name_collision",
                    message=f"{count} recipes share name='{name}'",
                    field="name",
                    metadata={"name": name, "count": count},
                )
            )
    return findings


def _validate_one(recipe: Recipe) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    src = recipe.metadata.get("source_file", "")

    def f(severity: str, code: str, message: str, field: str | None = None) -> ValidationFinding:
        return ValidationFinding(
            severity=severity,
            code=code,
            message=message,
            field=field,
            metadata={"name": recipe.name, "source_file": src},
        )

    # --- frontmatter basics ---
    if not recipe.name:
        findings.append(f("error", "missing_name", f"{src}: recipe has no name", "name"))
    elif not _NAME_RE.match(recipe.name):
        findings.append(f("warning", "non_canonical_name",
                          f"name '{recipe.name}' is not kebab-case or snake-case", "name"))

    if not _SEMVER_RE.match(recipe.version):
        findings.append(f("warning", "invalid_version",
                          f"version '{recipe.version}' is not SemVer (expected X.Y.Z)", "version"))

    if not recipe.description:
        findings.append(f("warning", "missing_description", "recipe has no description", "description"))
    elif len(recipe.description) < 10:
        findings.append(f("info", "short_description",
                          f"description '{recipe.description}' is shorter than 10 chars", "description"))

    if not recipe.steps:
        findings.append(f("error", "no_steps", "recipe declares no steps", "steps"))
        return findings

    # --- step ids ---
    step_ids = [s.id for s in recipe.steps]
    declared_ids = set(step_ids)
    for s in recipe.steps:
        if not s.id:
            findings.append(f("error", "missing_step_id", "a step has no id", "steps"))

    dup_steps = [sid for sid, c in Counter(i for i in step_ids if i).items() if c > 1]
    for sid in dup_steps:
        findings.append(f("error", "duplicate_step_id",
                          f"step id '{sid}' is used more than once", "steps"))

    declared_inputs = {i.name for i in recipe.inputs}

    # --- per-step reference integrity ---
    for s in recipe.steps:
        for dep in s.needs:
            if dep == s.id:
                findings.append(f("error", "self_dependency",
                                  f"step '{s.id}' lists itself in needs", "steps"))
            elif dep not in declared_ids:
                findings.append(f("error", "dangling_needs",
                                  f"step '{s.id}' needs unknown step '{dep}'", "steps"))

        for ref in referenced_step_ids(s.inputs):
            if ref == s.id:
                findings.append(f("error", "self_dependency",
                                  f"step '{s.id}' references its own output", "steps"))
            elif ref not in declared_ids:
                findings.append(f("error", "dangling_step_reference",
                                  f"step '{s.id}' references unknown step '${{steps.{ref}}}'", "steps"))

        for ref in referenced_input_names(s.inputs):
            if ref not in declared_inputs:
                findings.append(f("error", "dangling_input_reference",
                                  f"step '{s.id}' references undeclared input '${{inputs.{ref}}}'", "inputs"))

    # --- DAG analysis ---
    result = analyze(recipe)
    if not result.is_acyclic:
        cycle_str = " -> ".join(result.cycle)
        findings.append(f("error", "cyclic_dependency",
                          f"step dependency cycle detected: {cycle_str}", "steps"))

    # --- declared outputs must be produced by some step ---
    produced = {s.produces for s in recipe.steps if s.produces}
    for out in recipe.outputs:
        if out.name not in produced:
            findings.append(f("warning", "unproduced_output",
                              f"declared output '{out.name}' is not produced by any step", "outputs"))

    # --- unreachable steps (acyclic only): produce nothing and nobody needs them ---
    if result.is_acyclic:
        needed: set[str] = set()
        for deps in result.edges.values():
            needed.update(deps)
        for s in recipe.steps:
            if s.id and s.id not in needed and not s.produces:
                findings.append(f("info", "unreachable_step",
                                  f"step '{s.id}' produces nothing and no step depends on it", "steps"))

    return findings
