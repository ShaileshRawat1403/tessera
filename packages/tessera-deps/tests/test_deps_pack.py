from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_deps.pack import DepsPack
from tessera_deps.parsers import _python_pinning, _split_name_constraint
from tessera_deps.schema import Dependency

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE = REPO_ROOT / "examples" / "deps"


# ---------- primitives ----------


def test_split_name_constraint():
    assert _split_name_constraint("rich==13.7.0") == ("rich", "==13.7.0")
    assert _split_name_constraint("flask") == ("flask", "")
    assert _split_name_constraint("requests>=2.0 ; python_version>'3'")[0] == "requests"


def test_python_pinning():
    assert _python_pinning("==13.7.0") == "pinned"
    assert _python_pinning(">=0.12") == "ranged"
    assert _python_pinning("") == "unpinned"
    assert _python_pinning("*") == "unpinned"


# ---------- end-to-end ----------


def _run(tmp_path: Path):
    out = tmp_path / "deps_pack"
    ctx = RunContext(job_name="deps", output_dir=out)
    DepsPack().run(input_path=SAMPLE, ctx=ctx, options={})
    return out, ctx


def test_inventory(tmp_path: Path):
    out, _ = _run(tmp_path)
    deps = [json.loads(l) for l in (out / "dependencies.jsonl").read_text().splitlines()]
    by = {(d["ecosystem"], d["name"], d["source_file"]): d for d in deps}
    # python pinned/ranged/unpinned
    assert by[("python", "rich", "requirements.txt")]["pinning"] == "pinned"
    assert by[("python", "typer", "requirements.txt")]["pinning"] == "ranged"
    assert by[("python", "flask", "requirements.txt")]["pinning"] == "unpinned"
    # npm
    assert by[("npm", "react", "package.json")]["pinning"] == "ranged"
    assert by[("npm", "left-pad", "package.json")]["pinning"] == "unpinned"
    assert by[("npm", "jest", "package.json")]["pinning"] == "pinned"
    assert by[("npm", "jest", "package.json")]["scope"] == "dev"


def test_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "unpinned_dependency" in codes      # flask, left-pad
    assert "conflicting_constraint" in codes    # requests ==2.31.0 vs >=2.0
    assert "duplicate_dependency" in codes      # typer same constraint in both reqs files


def test_duplicates_report(tmp_path: Path):
    out, _ = _run(tmp_path)
    dup = (out / "duplicates.md").read_text()
    assert "requests" in dup
    assert "typer" in dup


def test_artifacts(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "dependencies.jsonl", "index.md", "validation_report.md",
        "coverage_report.md", "duplicates.md",
    } <= names


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "dependencies.jsonl").read_text().splitlines():
        d = Dependency.model_validate_json(line)
        assert d.name and d.ecosystem


def test_single_manifest_input(tmp_path: Path):
    out = tmp_path / "deps_pack"
    ctx = RunContext(job_name="deps", output_dir=out)
    DepsPack().run(input_path=SAMPLE / "requirements.txt", ctx=ctx, options={})
    deps = [json.loads(l) for l in (out / "dependencies.jsonl").read_text().splitlines()]
    names = {d["name"] for d in deps}
    assert {"rich", "typer", "flask", "requests"} <= names


# ---------- v0.2: lockfile-vs-manifest drift ----------
from tessera_deps.lockfiles import parse_lockfile  # noqa: E402


def test_parse_npm_lock():
    locked = parse_lockfile(SAMPLE / "package-lock.json")
    assert locked.get("react") == "18.2.0"
    assert locked.get("jest") == "29.0.0"
    assert "left-pad" not in locked


def test_declared_not_locked(tmp_path: Path):
    _, ctx = _run(tmp_path)
    drift = [f for f in ctx.metadata["findings"] if f.code == "declared_not_locked"]
    names = {f.metadata.get("name") for f in drift}
    # left-pad is declared in package.json but missing from the lockfile
    assert "left-pad" in names
    # react/jest are locked -> not flagged
    assert "react" not in names and "jest" not in names


def test_locked_mismatch(tmp_path: Path):
    proj = tmp_path / "mm"
    proj.mkdir()
    (proj / "package.json").write_text('{"name":"x","dependencies":{"foo":"1.2.3"}}', encoding="utf-8")
    (proj / "package-lock.json").write_text(
        '{"lockfileVersion":3,"packages":{"node_modules/foo":{"version":"1.2.9"}}}', encoding="utf-8"
    )
    out = tmp_path / "deps_pack"
    ctx = RunContext(job_name="deps", output_dir=out)
    DepsPack().run(input_path=proj, ctx=ctx, options={})
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "locked_version_mismatch" in codes


def test_lockfile_missing(tmp_path: Path):
    proj = tmp_path / "nolock"
    proj.mkdir()
    (proj / "package.json").write_text('{"name":"x","dependencies":{"foo":"^1.0.0"}}', encoding="utf-8")
    out = tmp_path / "deps_pack"
    ctx = RunContext(job_name="deps", output_dir=out)
    DepsPack().run(input_path=proj, ctx=ctx, options={})
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "lockfile_missing" in codes
