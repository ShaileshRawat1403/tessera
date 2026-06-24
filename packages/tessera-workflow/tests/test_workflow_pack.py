from __future__ import annotations

from pathlib import Path

import pytest

from tessera_core.models import RunContext
from tessera_workflow.pack import WorkflowPack

REPO_ROOT = Path(__file__).resolve().parents[3]
VALID_FIXTURE = REPO_ROOT / "examples" / "workflow" / "valid_codeops.workflow.yaml"
INVALID_FIXTURE = REPO_ROOT / "examples" / "workflow" / "invalid_no_governance.workflow.yaml"


def test_valid_workflow_produces_artifacts(tmp_path: Path) -> None:
    ctx = RunContext(job_name="workflow", output_dir=tmp_path / "out")
    pack = WorkflowPack()
    artifacts = pack.run(input_path=VALID_FIXTURE, ctx=ctx, options={})

    names = {a.name for a in artifacts}
    assert names == {"workflow_manifest.yaml", "governance_report.md"}
    for art in artifacts:
        assert art.path.exists()


def test_valid_workflow_no_errors(tmp_path: Path) -> None:
    ctx = RunContext(job_name="workflow", output_dir=tmp_path / "out")
    pack = WorkflowPack()
    pack.run(input_path=VALID_FIXTURE, ctx=ctx, options={})

    findings = ctx.metadata["findings"]
    errors = [f for f in findings if f.severity == "error"]
    assert not errors, f"unexpected errors: {[f.message for f in errors]}"


def test_valid_workflow_has_steps_in_report(tmp_path: Path) -> None:
    ctx = RunContext(job_name="workflow", output_dir=tmp_path / "out")
    pack = WorkflowPack()
    pack.run(input_path=VALID_FIXTURE, ctx=ctx, options={})

    report = (tmp_path / "out" / "governance_report.md").read_text()
    assert "codeops.repo_change.host_dev" in report
    assert "analyze_repo" in report
    assert "promote_draft_pr" in report
    assert "Review gates" in report or "review_gates" in report


def test_invalid_workflow_raises_governance_findings(tmp_path: Path) -> None:
    ctx = RunContext(job_name="workflow", output_dir=tmp_path / "out")
    pack = WorkflowPack()
    pack.run(input_path=INVALID_FIXTURE, ctx=ctx, options={})

    findings = ctx.metadata["findings"]
    codes = {f.code for f in findings}
    assert "missing_recursion_fence" in codes
    assert "promotion_without_review" in codes
    assert "missing_evidence_hash_invariant" in codes


def test_empty_steps_is_error(tmp_path: Path) -> None:
    import yaml
    wf_file = tmp_path / "empty.workflow.yaml"
    wf_file.write_text(yaml.dump({"name": "empty", "version": "0.1", "steps": []}))

    ctx = RunContext(job_name="workflow", output_dir=tmp_path / "out")
    pack = WorkflowPack()
    pack.run(input_path=wf_file, ctx=ctx, options={})

    codes = {f.code for f in ctx.metadata["findings"]}
    assert "no_steps" in codes


def test_review_gate_unknown_step_is_error(tmp_path: Path) -> None:
    import yaml
    wf_file = tmp_path / "bad_gate.workflow.yaml"
    wf_file.write_text(yaml.dump({
        "name": "bad_gate", "version": "0.1",
        "steps": [
            {"name": "build", "adapter": "shell", "outputs": ["build.tar.gz"]},
        ],
        "review_gates": [{"after_step": "nonexistent_step"}],
        "recursion_fence": {"protected_paths": ["kernel/"]},
        "evidence_policy": {"hash_invariant_steps": ["build"]},
    }))

    ctx = RunContext(job_name="workflow", output_dir=tmp_path / "out")
    pack = WorkflowPack()
    pack.run(input_path=wf_file, ctx=ctx, options={})

    codes = {f.code for f in ctx.metadata["findings"]}
    assert "review_gate_unknown_step" in codes


def test_undefined_adapter_is_warning(tmp_path: Path) -> None:
    import yaml
    wf_file = tmp_path / "undeclared.workflow.yaml"
    wf_file.write_text(yaml.dump({
        "name": "undeclared", "version": "0.1",
        "steps": [
            {"name": "run", "adapter": "mystery_adapter", "outputs": ["out.json"]},
        ],
        "required_adapters": ["known_adapter"],
        "recursion_fence": {"protected_paths": ["kernel/"]},
        "evidence_policy": {"hash_invariant_steps": ["run"]},
        "review_gates": [{"after_step": "run"}],
    }))

    ctx = RunContext(job_name="workflow", output_dir=tmp_path / "out")
    pack = WorkflowPack()
    pack.run(input_path=wf_file, ctx=ctx, options={})

    codes = {f.code for f in ctx.metadata["findings"]}
    assert "undefined_adapter" in codes


def test_directory_of_workflows(tmp_path: Path) -> None:
    import yaml
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    for i in range(3):
        wf = {
            "name": f"wf_{i}", "version": "0.1",
            "steps": [{"name": "step1", "adapter": "shell", "outputs": [f"out{i}.json"]}],
            "required_adapters": ["shell"],
            "recursion_fence": {"protected_paths": ["kernel/"]},
            "evidence_policy": {"hash_invariant_steps": ["step1"]},
            "review_gates": [{"after_step": "step1"}],
        }
        (wf_dir / f"wf_{i}.workflow.yaml").write_text(yaml.dump(wf))

    ctx = RunContext(job_name="workflow", output_dir=tmp_path / "out")
    pack = WorkflowPack()
    artifacts = pack.run(input_path=wf_dir, ctx=ctx, options={})
    assert len(artifacts) == 2

    report = (tmp_path / "out" / "governance_report.md").read_text()
    assert "Workflows validated: 3" in report
