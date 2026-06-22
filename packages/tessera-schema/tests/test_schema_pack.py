from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_schema.loader import _looks_like_schema, load_schema_records
from tessera_schema.pack import SchemaPack
from tessera_schema.schema import SchemaDoc

REPO_ROOT = Path(__file__).resolve().parents[3]
EX = REPO_ROOT / "examples" / "schema"


# ---------- detection ----------


def test_looks_like_schema():
    assert _looks_like_schema({"$schema": "x"})
    assert _looks_like_schema({"type": "object", "properties": {}})
    assert _looks_like_schema({"type": "string"})
    assert not _looks_like_schema({"name": "demo", "version": "1.0"})


# ---------- parsing ----------


def test_parse_person(tmp_path: Path):
    docs = load_schema_records(EX / "person.schema.json", {})
    d = docs[0]
    assert d.title == "Person"
    assert d.type == "object"
    assert "name" in d.properties and "age" in d.properties
    assert d.required == ["name"]
    assert d.additional_properties_set is True


# ---------- end-to-end ----------


def _run(tmp_path: Path):
    out = tmp_path / "schema_pack"
    ctx = RunContext(job_name="schema", output_dir=out)
    SchemaPack().run(input_path=EX, ctx=ctx, options={})
    return out, ctx


def test_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "required_not_in_properties" in codes   # broken: ghost
    assert "missing_schema_version" in codes         # broken: no $schema
    assert "missing_title" in codes                  # broken: no title
    assert "additional_properties_unset" in codes     # broken: not set


def test_clean_schema_has_no_errors_for_itself(tmp_path: Path):
    out, ctx = _run(tmp_path)
    # the person schema must not produce required_not_in_properties
    req_errs = [f for f in ctx.metadata["findings"]
                if f.code == "required_not_in_properties" and f.metadata.get("path", "").endswith("person.schema.json")]
    assert req_errs == []


def test_artifacts(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {"schemas.jsonl", "index.md", "validation_report.md", "coverage_report.md"} <= names
    docs = [json.loads(l) for l in (out / "schemas.jsonl").read_text().splitlines()]
    assert len(docs) == 2


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "schemas.jsonl").read_text().splitlines():
        d = SchemaDoc.model_validate_json(line)
        assert d.path
