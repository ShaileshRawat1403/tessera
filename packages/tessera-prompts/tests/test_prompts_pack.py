from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tessera_core.models import RunContext

from tessera_prompts.loader import discover_prompt_files, parse_prompt_file
from tessera_prompts.pack import PromptsPack
from tessera_prompts.validator import validate_prompts

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "examples" / "prompts"
BROKEN_DIR = Path(__file__).parent / "fixtures" / "broken"


# ---------- discovery ----------


def test_discovery_finds_both_file_and_dir_shapes():
    files = discover_prompt_files(EXAMPLES_DIR)
    names = {p.name for p in files}
    assert "refund_window.prompt.md" in names
    assert "code_review.prompt.md" in names
    assert "PROMPT.md" in names


def test_discovery_on_single_file_returns_that_file():
    files = discover_prompt_files(EXAMPLES_DIR / "refund_window.prompt.md")
    assert len(files) == 1


# ---------- parsing ----------


def test_parse_extracts_variables_from_body():
    case = parse_prompt_file(EXAMPLES_DIR / "refund_window.prompt.md")
    assert case.name == "refund_window"
    assert case.version == "1.0.0"
    assert "customer_name" in case.extracted_variables
    assert "days_since_purchase" in case.extracted_variables
    assert len(case.examples) == 2


def test_parse_dir_form_tags_source_form():
    case = parse_prompt_file(EXAMPLES_DIR / "translate" / "PROMPT.md")
    assert case.metadata["source_form"] == "directory"


def test_parse_file_form_tags_source_form():
    case = parse_prompt_file(EXAMPLES_DIR / "refund_window.prompt.md")
    assert case.metadata["source_form"] == "file"


# ---------- end-to-end pack run ----------


def test_pack_creates_expected_artifacts(tmp_path: Path):
    output_dir = tmp_path / "prompt_pack"
    ctx = RunContext(job_name="prompts", output_dir=output_dir)
    pack = PromptsPack()
    artifacts = pack.run(input_path=EXAMPLES_DIR, ctx=ctx, options={})

    names = {a.name for a in artifacts}
    assert names == {
        "index.jsonl",
        "examples.jsonl",
        "index.md",
        "validation_report.md",
        "coverage_report.md",
    }
    for art in artifacts:
        assert art.path.exists(), f"missing on disk: {art.name}"

    index = [json.loads(line) for line in (output_dir / "index.jsonl").read_text().splitlines()]
    assert len(index) == 3, "should find refund_window, code_review, translate"
    names_in_index = {c["name"] for c in index}
    assert names_in_index == {"refund_window", "code_review", "translate"}

    examples = [json.loads(line) for line in (output_dir / "examples.jsonl").read_text().splitlines()]
    assert len(examples) >= 4

    index_md = (output_dir / "index.md").read_text()
    assert "refund_window" in index_md
    assert "translate" in index_md


def test_pack_run_summary_has_no_errors_on_clean_examples(tmp_path: Path):
    output_dir = tmp_path / "prompt_pack"
    ctx = RunContext(job_name="prompts", output_dir=output_dir)
    PromptsPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    findings = ctx.metadata["findings"]
    errors = [f for f in findings if f.severity == "error"]
    assert errors == [], f"clean examples produced errors: {errors}"


# ---------- validation ----------


def _parse_broken_set() -> list:
    return [parse_prompt_file(p) for p in sorted(BROKEN_DIR.glob("*.prompt.md"))]


@pytest.mark.parametrize(
    "expected_code",
    [
        "missing_name",
        "undeclared_variable",
        "invalid_version",
        "example_missing_required_variable",
        "duplicate_name_version",
    ],
)
def test_validator_flags_known_issues(expected_code: str):
    cases = _parse_broken_set()
    findings = validate_prompts(cases)
    codes = {f.code for f in findings}
    assert expected_code in codes, f"expected {expected_code} in {codes}"


def test_examples_jsonl_renders_template(tmp_path: Path):
    output_dir = tmp_path / "prompt_pack"
    ctx = RunContext(job_name="prompts", output_dir=output_dir)
    PromptsPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    examples = [json.loads(line) for line in (output_dir / "examples.jsonl").read_text().splitlines()]
    refund = [e for e in examples if e["prompt_name"] == "refund_window"]
    assert refund
    rendered = refund[0]["rendered_prompt"]
    assert "{{customer_name}}" not in rendered
    assert "Maya" in rendered or "Arjun" in rendered


def test_index_jsonl_is_pydantic_serializable_round_trip(tmp_path: Path):
    """Confirm the canonical PromptCase round-trips through JSONL via pydantic."""
    output_dir = tmp_path / "prompt_pack"
    ctx = RunContext(job_name="prompts", output_dir=output_dir)
    PromptsPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    from tessera_prompts.schema import PromptCase

    for line in (output_dir / "index.jsonl").read_text().splitlines():
        restored = PromptCase.model_validate_json(line)
        assert restored.name
        assert restored.version
