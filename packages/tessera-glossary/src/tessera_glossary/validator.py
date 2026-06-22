from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_glossary.schema import Term


def validate_glossary_records(terms: list[Term], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not terms:
        findings.append(ValidationFinding(severity="info", code="no_vocabulary",
                                          message="no vocabulary extracted", field=None))
        return findings

    for cluster in options.get("_clusters", []):
        forms = cluster["forms"]
        forms_str = ", ".join(f"{k} ({v})" for k, v in forms.items())
        findings.append(
            ValidationFinding(
                severity="warning", code="terminology_inconsistency",
                message=(f"concept '{cluster['concept']}' is written {len(forms)} ways: "
                         f"{forms_str}; standardize on '{cluster['recommended']}'"),
                field="glossary",
                metadata={"concept": cluster["concept"], "forms": forms, "recommended": cluster["recommended"]},
            )
        )

    return findings
