from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_dockerfile.pack import DockerfilePack
from tessera_dockerfile.parse import is_dockerfile, parse_dockerfile
from tessera_dockerfile.schema import Instruction

REPO_ROOT = Path(__file__).resolve().parents[3]
EX = REPO_ROOT / "examples" / "dockerfile"
BAD = EX / "Dockerfile"
CLEAN = EX / "Dockerfile.multistage"


# ---------- parsing ----------


def test_is_dockerfile():
    assert is_dockerfile(Path("Dockerfile"))
    assert is_dockerfile(Path("Dockerfile.multistage"))
    assert is_dockerfile(Path("api.dockerfile"))
    assert not is_dockerfile(Path("app.py"))


def test_parse_line_continuation(tmp_path: Path):
    df = tmp_path / "Dockerfile"
    df.write_text("RUN apt-get update \\\n && apt-get install -y curl\n", encoding="utf-8")
    instrs = parse_dockerfile(df, "Dockerfile")
    runs = [i for i in instrs if i.instruction == "RUN"]
    assert len(runs) == 1
    assert "curl" in runs[0].argument


def test_parse_stage_names(tmp_path: Path):
    instrs = parse_dockerfile(CLEAN, "Dockerfile.multistage")
    froms = [i for i in instrs if i.instruction == "FROM"]
    assert any("AS base" in i.argument for i in froms)


# ---------- linting ----------


def _run(tmp_path: Path, target: Path):
    out = tmp_path / "dockerfile_pack"
    ctx = RunContext(job_name="dockerfile", output_dir=out)
    DockerfilePack().run(input_path=target, ctx=ctx, options={})
    return out, ctx


def test_bad_dockerfile_findings(tmp_path: Path):
    _, ctx = _run(tmp_path, BAD)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "latest_tag" in codes            # python:latest
    assert "secret_in_image" in codes        # API_TOKEN
    assert "add_instead_of_copy" in codes     # ADD ./app
    assert "runs_as_root" in codes            # no USER
    assert "missing_healthcheck" in codes     # no HEALTHCHECK


def test_clean_multistage_has_no_warnings(tmp_path: Path):
    _, ctx = _run(tmp_path, CLEAN)
    warnings = [f for f in ctx.metadata["findings"] if f.severity == "warning"]
    # base image pinned (3.12-slim), final references a stage, has USER -> no warnings
    codes = {f.code for f in warnings}
    assert "latest_tag" not in codes
    assert "unpinned_base_image" not in codes
    assert "runs_as_root" not in codes


def test_stage_reference_not_flagged_as_unpinned(tmp_path: Path):
    _, ctx = _run(tmp_path, CLEAN)
    unpinned = [f for f in ctx.metadata["findings"] if f.code == "unpinned_base_image"]
    assert unpinned == []   # "FROM base AS final" must not be flagged


def test_artifacts(tmp_path: Path):
    out, _ = _run(tmp_path, BAD)
    names = {p.name for p in out.iterdir()}
    assert {"instructions.jsonl", "index.md", "validation_report.md", "coverage_report.md"} <= names


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path, BAD)
    for line in (out / "instructions.jsonl").read_text().splitlines():
        i = Instruction.model_validate_json(line)
        assert i.instruction
