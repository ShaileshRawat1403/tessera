from __future__ import annotations

from collections import Counter
from typing import Any

from tessera_core.models import ValidationFinding

from tessera_openapi.schema import Endpoint


def validate_openapi_records(endpoints: list[Endpoint], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for err in options.get("_errors", []):
        findings.append(
            ValidationFinding(severity="error", code="invalid_spec",
                              message=err.get("error", "invalid spec"), field=None)
        )

    if not endpoints and not options.get("_errors"):
        findings.append(ValidationFinding(severity="warning", code="no_endpoints",
                                          message="spec declares no operations", field="paths"))

    # duplicate operationIds (cross-endpoint)
    op_ids = [e.operation_id for e in endpoints if e.operation_id]
    for op_id, count in Counter(op_ids).items():
        if count > 1:
            findings.append(
                ValidationFinding(severity="error", code="duplicate_operation_id",
                                  message=f"operationId '{op_id}' is used by {count} operations",
                                  field="operationId", metadata={"operation_id": op_id})
            )

    for e in endpoints:
        loc = f"{e.method} {e.path}"

        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field=None, metadata={"endpoint": loc})

        if not e.operation_id:
            f_ = f("warning", "missing_operation_id", f"{loc} has no operationId")
            findings.append(f_)

        if not e.summary:
            findings.append(f("info", "missing_summary", f"{loc} has no summary or description"))

        if not e.tags:
            findings.append(f("info", "no_tags", f"{loc} has no tags"))

        # path params must be declared
        declared = set(e.declared_path_params)
        for p in e.path_params:
            if p not in declared:
                findings.append(f("error", "path_param_not_declared",
                                  f"{loc} uses path parameter '{{{p}}}' but does not declare it"))
        # declared path params must appear in the template
        for p in declared:
            if p not in e.path_params:
                findings.append(f("warning", "declared_param_not_in_path",
                                  f"{loc} declares path parameter '{p}' not present in the path"))

        # success response
        if not any(code.startswith("2") or code == "default" for code in e.responses):
            findings.append(f("warning", "missing_2xx_response", f"{loc} declares no success (2xx) response"))

        if e.deprecated:
            findings.append(f("info", "deprecated_endpoint", f"{loc} is deprecated"))

        if not e.secured:
            findings.append(f("info", "no_security", f"{loc} has no security requirement"))

    return findings
