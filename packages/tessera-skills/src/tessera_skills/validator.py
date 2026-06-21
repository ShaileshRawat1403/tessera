from __future__ import annotations

import re
from collections import Counter

from tessera_core.models import ValidationFinding

from tessera_skills.overlap import find_overlaps
from tessera_skills.schema import SkillManifest

_NAME_RE = re.compile(r"^[a-z0-9]+([_-][a-z0-9]+)*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([+-][0-9A-Za-z.-]+)?$")
_TRIGGER_HINTS = (
    "use when", "use this when", "use this skill", "triggers", "trigger when",
    "invoke when", "for ", "when ", "whenever ", "to ", "creates", "generates",
    "validates", "reviews", "summarize", "summarise", "fixes", "produces",
    "configures",
)


def validate_skills(skills: list[SkillManifest]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for s in skills:
        findings.extend(_validate_one(s))

    name_counts = Counter(s.name for s in skills if s.name)
    for name, count in name_counts.items():
        if count > 1:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="name_collision",
                    message=f"{count} skills share name='{name}'",
                    field="name",
                    metadata={"name": name, "count": count},
                )
            )

    for pair in find_overlaps(skills):
        code = (
            "description_overlap_error"
            if pair.severity == "error"
            else "description_overlap_warning"
        )
        findings.append(
            ValidationFinding(
                severity=pair.severity,
                code=code,
                message=(
                    f"descriptions for '{pair.name_a}' and '{pair.name_b}' "
                    f"overlap (jaccard {pair.similarity:.2f}); the agent may pick the wrong skill"
                ),
                field="description",
                metadata={
                    "name_a": pair.name_a,
                    "name_b": pair.name_b,
                    "similarity": pair.similarity,
                },
            )
        )

    return findings


def _validate_one(skill: SkillManifest) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    src = skill.metadata.get("source_folder", "")

    def f(severity: str, code: str, message: str, field: str | None = None) -> ValidationFinding:
        return ValidationFinding(
            severity=severity,
            code=code,
            message=message,
            field=field,
            metadata={"name": skill.name, "source_folder": src},
        )

    if not skill.name:
        findings.append(f("error", "missing_name", f"{src}: SKILL.md has no name", "name"))
    elif not _NAME_RE.match(skill.name):
        findings.append(
            f("warning", "non_canonical_name",
              f"name '{skill.name}' is not kebab-case or snake-case", "name")
        )

    if not _SEMVER_RE.match(skill.version):
        findings.append(
            f("warning", "invalid_version",
              f"version '{skill.version}' is not SemVer (expected X.Y.Z)", "version")
        )

    if not skill.description:
        findings.append(f("error", "missing_description",
                          "SKILL.md has no description; the agent cannot match this skill", "description"))
    else:
        if len(skill.description) < 30:
            findings.append(
                f("warning", "short_description",
                  f"description is {len(skill.description)} chars; agents need detail to match reliably",
                  "description")
            )
        if not any(hint in skill.description.lower() for hint in _TRIGGER_HINTS):
            findings.append(
                f("info", "description_lacks_triggers",
                  "description does not include trigger phrasing (e.g. 'Use when ...') so it may not fire reliably",
                  "description")
            )

    if not skill.body.strip():
        findings.append(f("error", "empty_body", "SKILL.md body is empty", "body"))

    return findings
