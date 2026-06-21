from __future__ import annotations

import json
from pathlib import Path

from systemsdk_core.models import RunContext

from systemsdk_evals.pack import EvalsPack

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_CSV = REPO_ROOT / "examples" / "evals" / "support_logs.csv"


def test_evals_pack_creates_expected_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "eval_pack"
    ctx = RunContext(job_name="evals", output_dir=output_dir)

    pack = EvalsPack()
    artifacts = pack.run(
        input_path=SAMPLE_CSV,
        ctx=ctx,
        options={"task_type": "customer_support"},
    )

    artifact_names = {a.name for a in artifacts}
    assert artifact_names == {
        "dataset.jsonl",
        "golden_candidates.csv",
        "rubric.yaml",
        "coverage_report.md",
        "data_quality_report.md",
    }

    for art in artifacts:
        assert art.path.exists(), f"missing artifact on disk: {art.name}"

    dataset_lines = [json.loads(line) for line in (output_dir / "dataset.jsonl").read_text().splitlines()]
    assert len(dataset_lines) == 4, "should drop the duplicate row, keep 4 unique inputs"

    findings = ctx.metadata["findings"]
    codes = [f.code for f in findings]
    assert "duplicate_input" in codes
    assert "missing_expected_answer" in codes

    quality = (output_dir / "data_quality_report.md").read_text()
    assert "Column Detection" in quality
    assert "user_message" in quality
    assert "final_resolution" in quality
    assert "policy" in quality


def test_input_column_override_wins(tmp_path: Path) -> None:
    output_dir = tmp_path / "eval_pack"
    ctx = RunContext(job_name="evals", output_dir=output_dir)

    pack = EvalsPack()
    pack.run(
        input_path=SAMPLE_CSV,
        ctx=ctx,
        options={"task_type": "customer_support", "input_column": "user_message"},
    )

    quality = (output_dir / "data_quality_report.md").read_text()
    assert "manual override" in quality


def test_task_type_drives_rubric(tmp_path: Path) -> None:
    import yaml

    output_dir = tmp_path / "eval_pack"
    ctx = RunContext(job_name="evals", output_dir=output_dir)
    pack = EvalsPack()
    pack.run(
        input_path=SAMPLE_CSV,
        ctx=ctx,
        options={"task_type": "rag_qa"},
    )
    rubric = yaml.safe_load((output_dir / "rubric.yaml").read_text())
    assert rubric["task_type"] == "rag_qa"
    assert "citation_present" in rubric["dimensions"]
