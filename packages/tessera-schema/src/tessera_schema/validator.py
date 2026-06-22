from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_schema.schema import SchemaDoc


def validate_schema_records(docs: list[SchemaDoc], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for err in options.get("_parse_errors", []):
        findings.append(ValidationFinding(severity="error", code="parse_error",
                                          message=f"{err['path']}: {err['error']}", field=None))

    if not docs and not options.get("_parse_errors"):
        findings.append(ValidationFinding(severity="info", code="no_schemas",
                                          message="no JSON Schema documents found", field=None))
        return findings

    for d in docs:
        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="schema", metadata={"path": d.path})

        # required entries that are not declared as properties
        prop_set = set(d.properties)
        for r in d.required:
            if r not in prop_set:
                findings.append(f("error", "required_not_in_properties",
                                  f"{d.path}: required field '{r}' is not declared in properties"))

        if not d.schema_version:
            findings.append(f("info", "missing_schema_version",
                              f"{d.path}: no $schema dialect declared"))
        if not d.type:
            findings.append(f("warning", "missing_type",
                              f"{d.path}: root schema has no 'type'"))
        if d.type == "object":
            if not d.properties:
                findings.append(f("warning", "object_without_properties",
                                  f"{d.path}: type 'object' but no properties declared"))
            if not d.additional_properties_set:
                findings.append(f("info", "additional_properties_unset",
                                  f"{d.path}: 'additionalProperties' not set; the object is open by default"))
        if not d.title:
            findings.append(f("info", "missing_title", f"{d.path}: no title"))

    return findings
