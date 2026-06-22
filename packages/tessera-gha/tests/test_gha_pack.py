from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_gha.loader import discover_workflows, load_gha_records
from tessera_gha.pack import GhaPack
from tessera_gha.schema import WorkflowItem

REPO_ROOT = Path(__file__).resolve().parents[3]
EX = REPO_ROOT / "examples" / "gha"


# ---------- discovery / parse ----------


def test_discover_workflows():
    wfs = discover_workflows(EX)
    names = {p.name for p in wfs}
    assert names == {"ci.yml", "release.yml"}


def test_pin_detection():
    opts: dict = {}
    items = load_gha_records(EX, opts)
    uses = {(i.workflow, i.action): i for i in items if i.kind == "uses"}
    # release pins to a SHA, ci uses a tag
    ci_checkout = next(i for i in items if i.kind == "uses" and "ci.yml" in i.workflow)
    rel_checkout = next(i for i in items if i.kind == "uses" and "release.yml" in i.workflow)
    assert ci_checkout.action_pinned is False
    assert rel_checkout.action_pinned is True


def test_injection_detection():
    items = load_gha_records(EX, {})
    inj = [i for i in items if i.run_injection]
    assert any("ci.yml" in i.workflow for i in inj)


# ---------- end-to-end ----------


def _run(tmp_path: Path):
    out = tmp_path / "gha_pack"
    ctx = RunContext(job_name="gha", output_dir=out)
    GhaPack().run(input_path=EX, ctx=ctx, options={})
    return out, ctx


def test_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "risky_trigger" in codes          # ci: pull_request_target
    assert "unpinned_action" in codes         # ci: checkout@v4
    assert "script_injection_risk" in codes    # ci: run with github.event.issue.title
    assert "missing_permissions" in codes      # ci build
    assert "missing_timeout" in codes          # ci build


def test_clean_release_not_over_flagged(tmp_path: Path):
    _, ctx = _run(tmp_path)
    # the release workflow pins its action and sets permissions+timeout
    rel_unpinned = [
        f for f in ctx.metadata["findings"]
        if f.code == "unpinned_action" and f.metadata.get("workflow", "").endswith("release.yml")
    ]
    assert rel_unpinned == []


def test_artifacts(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "items.jsonl", "workflows.jsonl", "index.md",
        "validation_report.md", "coverage_report.md",
    } <= names


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "items.jsonl").read_text().splitlines():
        i = WorkflowItem.model_validate_json(line)
        assert i.workflow
