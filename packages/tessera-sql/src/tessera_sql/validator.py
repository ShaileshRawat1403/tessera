from __future__ import annotations

from typing import Any

from tessera_core.models import ValidationFinding

from tessera_sql.schema import SqlStatement, SqlTable


def validate_sql_records(statements: list[SqlStatement], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not statements:
        findings.append(ValidationFinding(severity="info", code="no_statements",
                                          message="no SQL statements found", field=None))
        return findings

    for s in statements:
        loc = f"{s.file}:{s.lineno}"

        def f(severity: str, code: str, message: str) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message,
                                     field="sql", metadata={"file": s.file, "lineno": s.lineno, "kind": s.kind})

        if s.kind == "delete" and s.flags.get("has_where") is False:
            findings.append(f("error", "delete_without_where",
                              f"{loc}: DELETE without WHERE removes every row"))
        if s.kind == "update" and s.flags.get("has_where") is False:
            findings.append(f("warning", "update_without_where",
                              f"{loc}: UPDATE without WHERE writes every row"))
        if s.kind == "drop" and not s.flags.get("if_exists"):
            findings.append(f("warning", "drop_without_if_exists",
                              f"{loc}: DROP without IF EXISTS fails if the object is absent"))
        if s.kind == "select" and s.flags.get("select_star"):
            findings.append(f("info", "select_star",
                              f"{loc}: SELECT * couples the query to column order/shape"))

    tables: list[SqlTable] = options.get("_tables", [])
    for t in tables:
        if not t.has_primary_key:
            findings.append(
                ValidationFinding(
                    severity="warning", code="table_without_primary_key",
                    message=f"{t.file}:{t.lineno}: table `{t.name}` has no PRIMARY KEY",
                    field="sql", metadata={"table": t.name, "file": t.file, "lineno": t.lineno},
                )
            )

    return findings
