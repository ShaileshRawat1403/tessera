from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera_core.models import RunContext

from tessera_evals.pack import EvalsPack

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_CSV = REPO_ROOT / "examples" / "evals" / "support_logs.csv"
MESSY_DIR = REPO_ROOT / "examples" / "evals" / "messy"


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


MESSY_CASES = [
    # (filename, expected_input_col, expected_expected_col, expected_context_col)
    ("compound_prefix.csv", "customer_question", "approved_answer", "policy_context"),
    ("wrapper_suffix.csv", "question_text", "expected_response", "source_text"),
    ("unusual_aliases.csv", "user_input", "ground_truth", "retrieved_snippet"),
    ("cryptic_kb.csv", "request_body", "team_resolution", "kb_article"),
]


@pytest.mark.parametrize("filename,exp_in,exp_exp,exp_ctx", MESSY_CASES)
def test_messy_csv_variants_detect_without_override(
    tmp_path: Path, filename: str, exp_in: str, exp_exp: str, exp_ctx: str
) -> None:
    """Acceptance: each messy variant compiles correctly with no manual override."""
    output_dir = tmp_path / filename.replace(".csv", "")
    ctx = RunContext(job_name="evals", output_dir=output_dir)
    pack = EvalsPack()
    artifacts = pack.run(
        input_path=MESSY_DIR / filename,
        ctx=ctx,
        options={"task_type": "customer_support"},
    )

    assert len(artifacts) == 5
    for art in artifacts:
        assert art.path.exists(), f"{filename}: missing {art.name}"

    detections = ctx.metadata.get("findings")
    assert detections is not None

    quality = (output_dir / "data_quality_report.md").read_text()
    assert exp_in in quality, f"{filename}: input column {exp_in} not picked"
    assert exp_exp in quality, f"{filename}: expected column {exp_exp} not picked"
    assert exp_ctx in quality, f"{filename}: context column {exp_ctx} not picked"

    dataset_lines = (output_dir / "dataset.jsonl").read_text().splitlines()
    assert len(dataset_lines) >= 3, f"{filename}: too few records compiled"


def test_messy_csv_quality_report_includes_column_analysis(tmp_path: Path) -> None:
    output_dir = tmp_path / "eval_pack"
    ctx = RunContext(job_name="evals", output_dir=output_dir)
    pack = EvalsPack()
    pack.run(
        input_path=MESSY_DIR / "compound_prefix.csv",
        ctx=ctx,
        options={"task_type": "customer_support"},
    )

    quality = (output_dir / "data_quality_report.md").read_text()
    assert "Column Analysis" in quality
    assert "Completeness" in quality
    assert "Avg length" in quality
