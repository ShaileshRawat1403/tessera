from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_rag.corpus import doc_id_for, load_corpus
from tessera_rag.pack import RagPack
from tessera_rag.schema import RagCase
from tessera_rag.validator import validate_rag_records

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "examples" / "rag"
BROKEN_DIR = Path(__file__).parent / "fixtures" / "broken"


# ---------- corpus ----------


def test_doc_id_is_relative_path_without_suffix():
    assert doc_id_for(Path("billing/disputes.md")) == "billing/disputes"
    assert doc_id_for(Path("refunds.md")) == "refunds"


def test_load_corpus_finds_nested_docs():
    docs = load_corpus(EXAMPLES_DIR / "corpus")
    ids = {d.id for d in docs}
    assert ids == {"refunds", "billing/disputes", "cancellation"}
    refunds = next(d for d in docs if d.id == "refunds")
    assert refunds.title == "Refund policy"
    assert refunds.char_count > 0
    assert len(refunds.sha256) == 64


# ---------- end-to-end (clean example) ----------


def test_pack_creates_expected_artifacts(tmp_path: Path):
    out = tmp_path / "rag_pack"
    ctx = RunContext(job_name="rag", output_dir=out)
    artifacts = RagPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})

    names = {a.name for a in artifacts}
    assert names == {
        "dataset.jsonl",
        "corpus_index.jsonl",
        "validation_report.md",
        "coverage_report.md",
        "retrieval_targets.md",
    }
    for a in artifacts:
        assert a.path.exists()

    dataset = [json.loads(line) for line in (out / "dataset.jsonl").read_text().splitlines()]
    assert len(dataset) == 4
    corpus = [json.loads(line) for line in (out / "corpus_index.jsonl").read_text().splitlines()]
    assert len(corpus) == 3


def test_clean_example_has_no_errors(tmp_path: Path):
    out = tmp_path / "rag_pack"
    ctx = RunContext(job_name="rag", output_dir=out)
    RagPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    errors = [f for f in ctx.metadata["findings"] if f.severity == "error"]
    assert errors == [], f"clean example produced errors: {errors}"


def test_q4_without_answer_flagged_for_review(tmp_path: Path):
    out = tmp_path / "rag_pack"
    ctx = RunContext(job_name="rag", output_dir=out)
    RagPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "query_without_expected_answer" in codes


def test_retrieval_targets_report_lists_titles(tmp_path: Path):
    out = tmp_path / "rag_pack"
    ctx = RunContext(job_name="rag", output_dir=out)
    RagPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    report = (out / "retrieval_targets.md").read_text()
    assert "Refund policy" in report
    assert "billing/disputes" in report


# ---------- validation (broken fixture) ----------


def test_broken_fixture_flags_dangling_orphan_and_no_target(tmp_path: Path):
    out = tmp_path / "rag_pack"
    ctx = RunContext(job_name="rag", output_dir=out)
    RagPack().run(input_path=BROKEN_DIR, ctx=ctx, options={})
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "dangling_doc_reference" in codes   # q2 -> ghost_doc
    assert "orphan_document" in codes          # orphan.md
    assert "query_without_relevant_docs" in codes  # q3


def test_index_jsonl_pydantic_round_trip(tmp_path: Path):
    out = tmp_path / "rag_pack"
    ctx = RunContext(job_name="rag", output_dir=out)
    RagPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    for line in (out / "dataset.jsonl").read_text().splitlines():
        restored = RagCase.model_validate_json(line)
        assert restored.id
        assert restored.query
