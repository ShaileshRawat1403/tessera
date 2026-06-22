"""Lightweight SQL parsing: strip comments, split statements, classify, extract.

Not a full SQL grammar. It strips comments, splits on top-level semicolons,
and uses keyword/regex heuristics to classify statements and pull out the
high-signal facts a migration reviewer cares about.
"""

from __future__ import annotations

import re

from tessera_sql.schema import SqlStatement, SqlTable

_LINE_COMMENT = re.compile(r"--[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_IDENT = r'[`"\[]?([A-Za-z_][A-Za-z0-9_.$]*)[`"\]]?'


def strip_comments(sql: str) -> str:
    sql = _BLOCK_COMMENT.sub(" ", sql)
    sql = _LINE_COMMENT.sub("", sql)
    return sql


def split_statements(sql: str) -> list[tuple[str, int]]:
    """Split into (statement_text, line_number) on top-level semicolons.

    Semicolons inside single/double quotes are ignored.
    """
    cleaned = strip_comments(sql)
    statements: list[tuple[str, int]] = []
    buf: list[str] = []
    line = 1
    start_line = 1
    quote: str | None = None
    for ch in cleaned:
        if ch == "\n":
            line += 1
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            continue
        if ch == ";":
            text = "".join(buf).strip()
            if text:
                statements.append((text, start_line))
            buf = []
            start_line = line
            continue
        if not buf and ch.strip() == "":
            start_line = line
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        statements.append((tail, start_line))
    return statements


def classify(stmt: str) -> tuple[str, str]:
    """Return (kind, target_name)."""
    s = stmt.lstrip()
    low = s.lower()

    def grab(pat: str) -> str:
        m = re.search(pat, s, re.IGNORECASE)
        return m.group(1) if m else ""

    if low.startswith("create") and re.search(r"create\s+(temp\w*\s+)?table", low):
        return "create_table", grab(rf"create\s+(?:temp\w*\s+)?table\s+(?:if\s+not\s+exists\s+)?{_IDENT}")
    if low.startswith("create") and "index" in low.split("(")[0]:
        return "create_index", grab(rf"index\s+(?:if\s+not\s+exists\s+)?{_IDENT}")
    if low.startswith("alter"):
        return "alter", grab(rf"alter\s+table\s+{_IDENT}")
    if low.startswith("drop"):
        return "drop", grab(rf"drop\s+\w+\s+(?:if\s+exists\s+)?{_IDENT}")
    if low.startswith("insert"):
        return "insert", grab(rf"insert\s+into\s+{_IDENT}")
    if low.startswith("update"):
        return "update", grab(rf"update\s+{_IDENT}")
    if low.startswith("delete"):
        return "delete", grab(rf"delete\s+from\s+{_IDENT}")
    if low.startswith("select") or low.startswith("with"):
        return "select", ""
    return "other", ""


def statement_flags(kind: str, stmt: str) -> dict:
    low = stmt.lower()
    flags: dict = {}
    if kind in ("update", "delete"):
        flags["has_where"] = bool(re.search(r"\bwhere\b", low))
    if kind == "drop":
        flags["if_exists"] = "if exists" in low
    if kind == "select":
        # SELECT * (not count(*))
        flags["select_star"] = bool(re.search(r"select\s+\*", low))
    return flags


def parse_create_table(stmt: str, target: str) -> SqlTable | None:
    m = re.search(r"\((.*)\)", stmt, re.DOTALL)
    if not m:
        return SqlTable(name=target, columns=[], has_primary_key=False)
    body = m.group(1)
    columns: list[str] = []
    has_pk = bool(re.search(r"primary\s+key", body, re.IGNORECASE))
    for part in _split_top_level(body):
        p = part.strip()
        if not p:
            continue
        low = p.lower()
        if low.startswith(("primary key", "foreign key", "unique", "constraint", "check", "index", "key ")):
            continue
        m2 = re.match(_IDENT, p)
        if m2:
            columns.append(m2.group(1))
            if "primary key" in low:
                has_pk = True
    return SqlTable(name=target, columns=columns, has_primary_key=has_pk)


def _split_top_level(body: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts
