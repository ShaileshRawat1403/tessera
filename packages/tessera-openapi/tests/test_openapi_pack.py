from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_openapi.pack import OpenApiPack
from tessera_openapi.schema import Endpoint
from tessera_openapi.spec import path_params_in

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC = REPO_ROOT / "examples" / "openapi" / "petstore.yaml"


def _run(tmp_path: Path):
    out = tmp_path / "openapi_pack"
    ctx = RunContext(job_name="openapi", output_dir=out)
    OpenApiPack().run(input_path=SPEC, ctx=ctx, options={})
    return out, ctx


# ---------- parsing ----------


def test_path_params_extraction():
    assert path_params_in("/pets/{petId}/toys/{toyId}") == ["petId", "toyId"]
    assert path_params_in("/pets") == []


def test_endpoints_parsed(tmp_path: Path):
    out, ctx = _run(tmp_path)
    rows = [json.loads(l) for l in (out / "endpoints.jsonl").read_text().splitlines()]
    assert len(rows) == 4
    keyed = {(r["method"], r["path"]) for r in rows}
    assert ("GET", "/pets") in keyed
    assert ("POST", "/pets") in keyed
    assert ("GET", "/pets/{petId}") in keyed
    assert ("DELETE", "/pets/{petId}") in keyed


# ---------- lint findings ----------


def test_lint_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "duplicate_operation_id" in codes      # listPets twice
    assert "missing_operation_id" in codes        # POST /pets
    assert "missing_summary" in codes             # POST /pets
    assert "path_param_not_declared" in codes     # GET /pets/{petId}
    assert "missing_2xx_response" in codes         # POST /pets (only 400)
    assert "deprecated_endpoint" in codes          # DELETE /pets/{petId}


def test_properly_declared_param_not_flagged(tmp_path: Path):
    """DELETE /pets/{petId} declares petId, so it must not raise path_param_not_declared."""
    _, ctx = _run(tmp_path)
    bad = [
        f for f in ctx.metadata["findings"]
        if f.code == "path_param_not_declared" and f.metadata.get("endpoint") == "DELETE /pets/{petId}"
    ]
    assert bad == []


# ---------- artifacts ----------


def test_artifacts_and_surface(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "endpoints.jsonl", "index.md", "validation_report.md",
        "coverage_report.md", "surface.md",
    } <= names
    surface = (out / "surface.md").read_text()
    assert "## pets" in surface
    index = (out / "index.md").read_text()
    assert "Petstore" in index


def test_endpoint_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "endpoints.jsonl").read_text().splitlines():
        e = Endpoint.model_validate_json(line)
        assert e.method and e.path


def test_invalid_spec_flagged(tmp_path: Path):
    bad = tmp_path / "not_a_spec.yaml"
    bad.write_text("just: some\nrandom: yaml\n", encoding="utf-8")
    out = tmp_path / "op"
    ctx = RunContext(job_name="openapi", output_dir=out)
    OpenApiPack().run(input_path=bad, ctx=ctx, options={})
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "invalid_spec" in codes
