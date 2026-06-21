from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera_core.models import RunContext

from tessera_evals.adapters import (
    TARGETS,
    export,
    export_all,
    load_dataset,
    to_deepeval,
    to_langsmith,
    to_openai_evals,
    to_ragas,
)
from tessera_evals.pack import EvalsPack
from tessera_evals.schema import EvalRecord

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_CSV = REPO_ROOT / "examples" / "evals" / "support_logs.csv"


def _records() -> list[EvalRecord]:
    return [
        EvalRecord(
            id="t1",
            task_type="customer_support",
            input={"user_message": "Can I get a refund after 45 days?"},
            context={"source_text": "Refunds within 30 days."},
            expected={"mode": "reference", "reference_answer": "Outside the window.", "review_status": "source_extracted"},
        ),
        EvalRecord(
            id="t2",
            task_type="customer_support",
            input={"user_message": "My app crashes on login."},
            context={},
            expected={"mode": "candidate", "reference_answer": "", "review_status": "needs_human_review"},
        ),
    ]


def test_deepeval_shape():
    out = json.loads(to_deepeval(_records()))
    assert "goldens" in out
    g0 = out["goldens"][0]
    assert g0["input"] == "Can I get a refund after 45 days?"
    assert g0["expected_output"] == "Outside the window."
    assert g0["context"] == ["Refunds within 30 days."]
    # empty expected becomes null, missing context becomes null
    assert out["goldens"][1]["expected_output"] is None
    assert out["goldens"][1]["context"] is None


def test_ragas_shape():
    lines = to_ragas(_records()).strip().splitlines()
    row0 = json.loads(lines[0])
    assert row0["question"] == "Can I get a refund after 45 days?"
    assert row0["ground_truth"] == "Outside the window."
    assert row0["contexts"] == ["Refunds within 30 days."]


def test_openai_evals_shape():
    lines = to_openai_evals(_records()).strip().splitlines()
    row0 = json.loads(lines[0])
    assert row0["input"] == [{"role": "user", "content": "Can I get a refund after 45 days?"}]
    assert row0["ideal"] == "Outside the window."


def test_langsmith_shape():
    lines = to_langsmith(_records()).strip().splitlines()
    row0 = json.loads(lines[0])
    assert row0["inputs"]["input"] == "Can I get a refund after 45 days?"
    assert row0["outputs"]["expected"] == "Outside the window."


def test_export_all_writes_four_files(tmp_path: Path):
    paths = export_all(_records(), tmp_path)
    names = {p.name for p in paths}
    assert names == {
        "deepeval_goldens.json",
        "ragas_dataset.jsonl",
        "openai_evals_samples.jsonl",
        "langsmith_examples.jsonl",
    }
    for p in paths:
        assert p.exists() and p.read_text().strip()


def test_export_unknown_target_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        export(_records(), "nonexistent", tmp_path)


def test_full_chain_compile_then_export(tmp_path: Path):
    """compile a CSV to dataset.jsonl, then export it to every framework."""
    eval_out = tmp_path / "eval_pack"
    ctx = RunContext(job_name="evals", output_dir=eval_out)
    EvalsPack().run(input_path=SAMPLE_CSV, ctx=ctx, options={"task_type": "customer_support"})

    dataset = eval_out / "dataset.jsonl"
    assert dataset.exists()

    loaded = load_dataset(dataset)
    assert loaded

    export_dir = tmp_path / "export"
    paths = export_all(loaded, export_dir)
    assert len(paths) == len(TARGETS)
    # deepeval file is valid JSON; the others are valid JSONL
    json.loads((export_dir / "deepeval_goldens.json").read_text())
    for fname in ("ragas_dataset.jsonl", "openai_evals_samples.jsonl", "langsmith_examples.jsonl"):
        for line in (export_dir / fname).read_text().splitlines():
            json.loads(line)
