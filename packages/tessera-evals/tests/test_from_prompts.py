from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera_core.models import RunContext

from tessera_evals.from_prompts import load_prompt_examples, resolve_examples_path
from tessera_evals.pack import EvalsPack

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPTS_EXAMPLES_DIR = REPO_ROOT / "examples" / "prompts"

# Skip the cross-pack chain tests gracefully if tessera-prompts is not installed.
prompts_pack = pytest.importorskip(
    "tessera_prompts.pack",
    reason="tessera-prompts not installed; cross-pack interop test skipped",
)
PromptsPack = prompts_pack.PromptsPack


def _build_prompt_pack(tmp_path: Path) -> Path:
    out = tmp_path / "prompt_pack"
    ctx = RunContext(job_name="prompts", output_dir=out)
    PromptsPack().run(input_path=PROMPTS_EXAMPLES_DIR, ctx=ctx, options={})
    return out


def test_resolve_examples_path_accepts_dir_and_file(tmp_path: Path):
    pack = _build_prompt_pack(tmp_path)
    # directory form resolves to the examples.jsonl inside
    assert resolve_examples_path(pack).name == "examples.jsonl"
    # file form passes through
    direct = pack / "examples.jsonl"
    assert resolve_examples_path(direct) == direct


def test_load_prompt_examples_maps_to_eval_records(tmp_path: Path):
    pack = _build_prompt_pack(tmp_path)
    options: dict = {"task_type": "customer_support"}
    records = load_prompt_examples(pack, options)

    assert records, "expected records ingested from prompt examples"
    assert options["_source"] == "prompts"

    # every record carries prompt provenance
    for r in records:
        assert r.metadata["origin"] == "prompts"
        assert r.metadata["prompt_name"]
        assert r.input.get("user_message")


def test_full_chain_prompts_to_evals(tmp_path: Path):
    """The headline composition test: prompts pack output feeds the evals pack."""
    prompt_pack = _build_prompt_pack(tmp_path)

    eval_out = tmp_path / "eval_pack"
    ctx = RunContext(job_name="evals", output_dir=eval_out)
    artifacts = EvalsPack().run(
        input_path=prompt_pack,  # directory containing examples.jsonl
        ctx=ctx,
        options={"task_type": "customer_support", "source": "prompts"},
    )

    names = {a.name for a in artifacts}
    assert names == {
        "dataset.jsonl",
        "golden_candidates.csv",
        "rubric.yaml",
        "coverage_report.md",
        "data_quality_report.md",
    }

    dataset = [json.loads(line) for line in (eval_out / "dataset.jsonl").read_text().splitlines()]
    assert dataset, "expected eval records derived from prompt examples"

    # refund_window has two examples with expected answers; they should arrive
    # as source_extracted references, not needs_human_review.
    refund = [r for r in dataset if r["metadata"].get("prompt_name") == "refund_window"]
    assert refund
    assert any(r["expected"]["review_status"] == "source_extracted" for r in refund)

    quality = (eval_out / "data_quality_report.md").read_text()
    assert "prompts examples.jsonl" in quality
    assert "Field Mapping" in quality
    # no spurious column-detection error on this source
    assert "missing_input_column" not in quality


def test_prompts_source_does_not_emit_column_findings(tmp_path: Path):
    prompt_pack = _build_prompt_pack(tmp_path)
    ctx = RunContext(job_name="evals", output_dir=tmp_path / "eval_pack")
    EvalsPack().run(
        input_path=prompt_pack,
        ctx=ctx,
        options={"task_type": "rag_qa", "source": "prompts"},
    )
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "missing_input_column" not in codes
    assert "missing_context_column" not in codes
