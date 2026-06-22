from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_docs.schema import DocSymbol

LOW_COVERAGE_THRESHOLD = 0.80


def validate_docs_records(symbols: list[DocSymbol], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for err in options.get("_parse_errors", []):
        findings.append(
            ValidationFinding(severity="error", code="parse_error",
                              message=f"could not parse: {err}", field=None)
        )

    public = [s for s in symbols if s.is_public]
    if not public:
        if not options.get("_parse_errors"):
            findings.append(ValidationFinding(severity="info", code="no_public_symbols",
                                              message="no public symbols found", field=None))
        return findings

    code_for_kind = {
        "module": "missing_module_docstring",
        "class": "missing_class_docstring",
        "function": "missing_function_docstring",
        "method": "missing_method_docstring",
    }
    severity_for_kind = {
        "module": "info",
        "class": "warning",
        "function": "warning",
        "method": "warning",
    }

    for s in public:
        if not s.has_docstring:
            findings.append(
                ValidationFinding(
                    severity=severity_for_kind.get(s.kind, "warning"),
                    code=code_for_kind.get(s.kind, "missing_docstring"),
                    message=f"{s.kind} `{s.qualname or s.name}` ({s.path}:{s.lineno}) has no docstring",
                    field="docs",
                    metadata={"path": s.path, "qualname": s.qualname or s.name, "kind": s.kind, "lineno": s.lineno},
                )
            )

    documented = sum(1 for s in public if s.has_docstring)
    coverage = documented / len(public)
    if coverage < LOW_COVERAGE_THRESHOLD:
        findings.append(
            ValidationFinding(
                severity="warning", code="low_doc_coverage",
                message=f"public docstring coverage is {coverage*100:.0f}% (below {int(LOW_COVERAGE_THRESHOLD*100)}%)",
                field="docs", metadata={"coverage": round(coverage, 4)},
            )
        )

    return findings
