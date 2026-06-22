from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_todo.schema import TodoItem


def validate_todo_records(items: list[TodoItem], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not items:
        findings.append(ValidationFinding(severity="info", code="no_markers",
                                          message="no TODO/FIXME-style markers found", field=None))
        return findings

    for it in items:
        loc = f"{it.file}:{it.lineno}"

        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="todo", metadata={"file": it.file, "lineno": it.lineno, "marker": it.marker})

        if it.priority == "high":
            findings.append(f("warning", "high_priority_marker",
                              f"{loc}: {it.marker} — {it.text or '(no description)'}"))
        if it.marker == "TODO" and not it.owner:
            findings.append(f("info", "todo_without_owner",
                              f"{loc}: TODO has no owner; add TODO(name): ..."))
        if not it.text:
            findings.append(f("info", "marker_without_text",
                              f"{loc}: {it.marker} has no description"))

    return findings
