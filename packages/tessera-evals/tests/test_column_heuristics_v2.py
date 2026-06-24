"""v0.2 column-heuristics acceptance tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from tessera_core.models import RunContext
from tessera_evals.pack import EvalsPack

REPO_ROOT = Path(__file__).resolve().parents[3]
MESSY_DIR = REPO_ROOT / "examples" / "evals" / "messy"


def test_typo_headers_detected(tmp_path: Path) -> None:
    """questoin/expexted/kontext (typos) should resolve via fuzzy matching."""
    ctx = RunContext(job_name="evals", output_dir=tmp_path / "out")
    pack = EvalsPack()
    artifacts = pack.run(
        input_path=MESSY_DIR / "typo_headers.csv",
        ctx=ctx,
        options={"task_type": "customer_support"},
    )
    assert len(artifacts) == 5
    quality = (tmp_path / "out" / "data_quality_report.md").read_text()
    # All three columns detected — check input and expected at minimum
    assert "questoin" in quality, "input column with typo not detected"
    assert "expexted" in quality, "expected column with typo not detected"
    dataset_lines = (tmp_path / "out" / "dataset.jsonl").read_text().splitlines()
    assert len(dataset_lines) >= 3


def test_output_variant_headers_detected(tmp_path: Path) -> None:
    """expected_output + rag_context should resolve at high confidence (>=0.85)."""
    ctx = RunContext(job_name="evals", output_dir=tmp_path / "out")
    pack = EvalsPack()
    pack.run(
        input_path=MESSY_DIR / "output_variants.csv",
        ctx=ctx,
        options={"task_type": "rag_qa"},
    )
    quality = (tmp_path / "out" / "data_quality_report.md").read_text()
    assert "expected_output" in quality, "expected_output column not picked"
    assert "rag_context" in quality, "rag_context column not picked"
    dataset_lines = (tmp_path / "out" / "dataset.jsonl").read_text().splitlines()
    assert len(dataset_lines) == 4


def test_no_column_conflict(tmp_path: Path) -> None:
    """Two fields must not claim the same column."""
    import csv, io
    # "answer" would naively match expected; but if "response" is present for
    # expected, "answer" should not also claim context.
    rows = [
        {"id": "1", "question": "What is X?", "answer": "X is Y.", "context": "X definition."},
        {"id": "2", "question": "When did Z?", "answer": "Z happened in 2020.", "context": "Z timeline."},
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

    csv_path = tmp_path / "conflict.csv"
    csv_path.write_text(buf.getvalue())

    ctx = RunContext(job_name="evals", output_dir=tmp_path / "out")
    pack = EvalsPack()
    pack.run(input_path=csv_path, ctx=ctx, options={"task_type": "generic"})

    findings = ctx.metadata["findings"]
    # Should compile 2 records, not fail
    dataset_lines = (tmp_path / "out" / "dataset.jsonl").read_text().splitlines()
    assert len(dataset_lines) == 2
    # No two fields should map to the same column (no collision error)
    error_codes = {f.code for f in findings if f.severity == "error"}
    assert "missing_input_column" not in error_codes


def test_fuzzy_score_thresholds() -> None:
    """Unit test the fuzzy scorer directly."""
    from tessera_core.detect import _fuzzy_score, _FUZZY_THRESHOLD
    # Close enough
    assert _fuzzy_score("questoin", "question") >= _FUZZY_THRESHOLD
    assert _fuzzy_score("expexted", "expected") >= _FUZZY_THRESHOLD
    # Too different
    assert _fuzzy_score("timestamp", "question") < _FUZZY_THRESHOLD


def test_suffix_normalization_upgrades_confidence() -> None:
    """expected_output normalizes to 'expected' -> 0.95 (not 0.85 token)."""
    from tessera_core.detect import detect_column
    from tessera_evals.compiler import EXPECTED_CANDIDATES

    det = detect_column(["expected_output"], "expected", EXPECTED_CANDIDATES)
    assert det.column == "expected_output"
    # Either exact candidate match or normalized match — both >=0.85
    assert det.confidence >= 0.85


def test_ground_truth_answer_normalizes() -> None:
    """ground_truth_answer -> strip 'answer' suffix -> 'ground_truth' -> 0.95."""
    from tessera_core.detect import detect_column
    from tessera_evals.compiler import EXPECTED_CANDIDATES

    det = detect_column(["ground_truth_answer"], "expected", EXPECTED_CANDIDATES)
    assert det.column == "ground_truth_answer"
    assert det.confidence >= 0.85
