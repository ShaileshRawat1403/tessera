from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_sql.pack import SqlPack
from tessera_sql.parse import classify, parse_create_table, split_statements, statement_flags
from tessera_sql.schema import SqlStatement

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE = REPO_ROOT / "examples" / "sql" / "schema.sql"


# ---------- parsing ----------


def test_split_ignores_semicolons_in_strings():
    sql = "INSERT INTO t VALUES ('a;b'); SELECT 1;"
    stmts = [s for s, _ in split_statements(sql)]
    assert len(stmts) == 2
    assert "a;b" in stmts[0]


def test_split_strips_comments():
    sql = "-- a comment\nSELECT 1; /* block\ncomment */ SELECT 2;"
    stmts = [s for s, _ in split_statements(sql)]
    assert len(stmts) == 2
    assert "comment" not in " ".join(stmts)


def test_classify_kinds():
    assert classify("CREATE TABLE users (id int)")[0] == "create_table"
    assert classify("create index idx on t(a)")[0] == "create_index"
    assert classify("ALTER TABLE users ADD COLUMN x int")[0] == "alter"
    assert classify("DROP TABLE t")[0] == "drop"
    assert classify("DELETE FROM t")[0] == "delete"
    assert classify("UPDATE t SET a=1")[0] == "update"
    assert classify("SELECT * FROM t")[0] == "select"


def test_classify_targets():
    assert classify("CREATE TABLE users (id int)")[1] == "users"
    assert classify("DELETE FROM sessions WHERE x=1")[1] == "sessions"


def test_flags():
    assert statement_flags("delete", "DELETE FROM t")["has_where"] is False
    assert statement_flags("delete", "DELETE FROM t WHERE a=1")["has_where"] is True
    assert statement_flags("drop", "DROP TABLE t")["if_exists"] is False
    assert statement_flags("drop", "DROP TABLE IF EXISTS t")["if_exists"] is True
    assert statement_flags("select", "SELECT * FROM t")["select_star"] is True


def test_parse_create_table_columns_and_pk():
    t = parse_create_table("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)", "users")
    assert t.name == "users"
    assert "id" in t.columns and "email" in t.columns
    assert t.has_primary_key is True

    t2 = parse_create_table("CREATE TABLE logs (message TEXT, created_at TIMESTAMP)", "logs")
    assert t2.has_primary_key is False


# ---------- end-to-end ----------


def _run(tmp_path: Path):
    out = tmp_path / "sql_pack"
    ctx = RunContext(job_name="sql", output_dir=out)
    SqlPack().run(input_path=SAMPLE, ctx=ctx, options={})
    return out, ctx


def test_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "delete_without_where" in codes        # DELETE FROM sessions;
    assert "update_without_where" in codes         # UPDATE users SET active=false;
    assert "drop_without_if_exists" in codes        # DROP TABLE temp_data;
    assert "table_without_primary_key" in codes     # logs
    assert "select_star" in codes                   # SELECT * FROM users


def test_safe_statements_not_flagged(tmp_path: Path):
    _, ctx = _run(tmp_path)
    # guarded delete + guarded drop should not raise their dangerous-variant codes for those lines
    delete_findings = [f for f in ctx.metadata["findings"] if f.code == "delete_without_where"]
    # only the unguarded DELETE should be flagged, not the WHERE one
    assert len(delete_findings) == 1


def test_artifacts_and_tables(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "statements.jsonl", "tables.jsonl", "index.md",
        "validation_report.md", "coverage_report.md", "tables.md",
    } <= names
    tables = [json.loads(l) for l in (out / "tables.jsonl").read_text().splitlines()]
    by_name = {t["name"]: t for t in tables}
    assert by_name["users"]["has_primary_key"] is True
    assert by_name["logs"]["has_primary_key"] is False


def test_statement_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "statements.jsonl").read_text().splitlines():
        s = SqlStatement.model_validate_json(line)
        assert s.kind
