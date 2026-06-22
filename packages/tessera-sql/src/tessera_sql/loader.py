from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_sql.parse import (
    classify,
    parse_create_table,
    split_statements,
    statement_flags,
)
from tessera_sql.schema import SqlStatement, SqlTable

_IGNORE = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".tox", "target",
}


def discover_sql_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    out: list[Path] = []
    for p in sorted(root.rglob("*.sql")):
        if any(part in _IGNORE for part in p.relative_to(root).parts):
            continue
        out.append(p)
    return out


def load_sql_records(input_path: Path, options: dict[str, Any]) -> list[SqlStatement]:
    """Parse SQL files into statements; stash discovered tables in options."""
    root = input_path if input_path.is_dir() else input_path.parent
    files = discover_sql_files(input_path if input_path.is_file() else root)

    statements: list[SqlStatement] = []
    tables: list[SqlTable] = []

    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = f.relative_to(root).as_posix() if f.is_relative_to(root) else f.name
        for stmt_text, lineno in split_statements(text):
            kind, target = classify(stmt_text)
            flags = statement_flags(kind, stmt_text)
            preview = " ".join(stmt_text.split())[:100]
            statements.append(
                SqlStatement(kind=kind, target=target, file=rel, lineno=lineno, preview=preview, flags=flags)
            )
            if kind == "create_table":
                t = parse_create_table(stmt_text, target)
                if t is not None:
                    t.file = rel
                    t.lineno = lineno
                    tables.append(t)

    options["_tables"] = tables
    options["_file_count"] = len(files)
    options["_root"] = str(root)
    return statements
