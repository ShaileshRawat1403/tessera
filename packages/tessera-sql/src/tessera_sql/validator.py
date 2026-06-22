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

        # --- migration-safety rules (the costly, easy-to-miss ones) ---
        if s.kind == "truncate":
            findings.append(f("warning", "truncate_table",
                              f"{loc}: TRUNCATE removes all rows and is often non-transactional / non-reversible"))
        if s.kind == "alter" and s.flags.get("add_not_null_without_default"):
            findings.append(f("error", "add_not_null_without_default",
                              f"{loc}: ADD COLUMN NOT NULL without DEFAULT rewrites the table and fails on existing rows"))
        if s.kind == "alter" and s.flags.get("drops_column"):
            findings.append(f("warning", "drop_column",
                              f"{loc}: dropping a column is destructive and irreversible; ensure no code still reads it"))
        if s.kind == "alter" and s.flags.get("renames"):
            findings.append(f("warning", "rename_breaks_compatibility",
                              f"{loc}: RENAME breaks any code/queries referencing the old name; prefer add-new + backfill + drop-old"))
        if s.kind == "create_table" and not s.flags.get("if_not_exists"):
            findings.append(f("info", "create_table_without_if_not_exists",
                              f"{loc}: CREATE TABLE without IF NOT EXISTS is not idempotent if the migration re-runs"))

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
