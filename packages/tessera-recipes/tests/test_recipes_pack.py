from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera_core.models import RunContext

from tessera_recipes.graph import analyze, extract_references, referenced_step_ids
from tessera_recipes.loader import discover_recipe_files, parse_recipe_file
from tessera_recipes.pack import RecipesPack
from tessera_recipes.schema import Recipe, RecipeStep
from tessera_recipes.validator import validate_recipes

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "examples" / "recipes"
BROKEN_DIR = Path(__file__).parent / "fixtures" / "broken"


# ---------- reference parsing ----------


def test_extract_references_finds_inputs_and_steps():
    refs = extract_references({"a": "${inputs.x}", "b": "${steps.collect.output}"})
    kinds = {(r.kind, r.target) for r in refs}
    assert ("inputs", "x") in kinds
    assert ("steps", "collect") in kinds


def test_extract_references_walks_nested_structures():
    refs = extract_references({"a": ["${steps.s1}", {"deep": "${steps.s2.output}"}]})
    targets = {r.target for r in refs if r.kind == "steps"}
    assert targets == {"s1", "s2"}


def test_referenced_step_ids():
    assert referenced_step_ids({"x": "${steps.foo.output}"}) == {"foo"}


# ---------- graph analysis ----------


def _recipe(steps: list[RecipeStep]) -> Recipe:
    return Recipe(name="r", steps=steps)


def test_linear_chain_topological_order():
    r = _recipe([
        RecipeStep(id="a", produces="oa"),
        RecipeStep(id="b", needs=["a"]),
        RecipeStep(id="c", needs=["b"]),
    ])
    result = analyze(r)
    assert result.is_acyclic
    assert result.order == ["a", "b", "c"]


def test_inferred_edges_from_references():
    r = _recipe([
        RecipeStep(id="a", produces="oa"),
        RecipeStep(id="b", inputs={"x": "${steps.a.output}"}),
    ])
    result = analyze(r)
    assert result.order == ["a", "b"]
    assert result.edges["b"] == ["a"]


def test_diamond_orders_root_first_and_join_last():
    r = _recipe([
        RecipeStep(id="root", produces="r"),
        RecipeStep(id="left", needs=["root"]),
        RecipeStep(id="right", needs=["root"]),
        RecipeStep(id="join", needs=["left", "right"]),
    ])
    result = analyze(r)
    assert result.is_acyclic
    assert result.order[0] == "root"
    assert result.order[-1] == "join"
    assert result.order.index("left") < result.order.index("join")
    assert result.order.index("right") < result.order.index("join")


def test_cycle_is_detected_and_reported():
    r = _recipe([
        RecipeStep(id="a", needs=["c"]),
        RecipeStep(id="b", needs=["a"]),
        RecipeStep(id="c", needs=["b"]),
    ])
    result = analyze(r)
    assert not result.is_acyclic
    assert result.order == []
    assert set(result.cycle) >= {"a", "b", "c"}


# ---------- discovery + parse ----------


def test_discovery_finds_file_and_folder_forms():
    files = discover_recipe_files(EXAMPLES_DIR)
    names = {p.name for p in files}
    assert "release-notes.recipe.md" in names
    assert "RECIPE.md" in names


def test_parse_reads_steps_and_io():
    r = parse_recipe_file(EXAMPLES_DIR / "release-notes.recipe.md")
    assert r.name == "release-notes"
    assert [s.id for s in r.steps] == ["collect", "summarize", "publish"]
    assert {i.name for i in r.inputs} == {"since_tag"}
    assert {o.name for o in r.outputs} == {"published_url"}


def test_parse_folder_form_tags_source_form():
    r = parse_recipe_file(EXAMPLES_DIR / "onboard-repo" / "RECIPE.md")
    assert r.metadata["source_form"] == "directory"


# ---------- end-to-end ----------


def test_pack_creates_expected_artifacts(tmp_path: Path):
    output_dir = tmp_path / "recipe_pack"
    ctx = RunContext(job_name="recipes", output_dir=output_dir)
    artifacts = RecipesPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})

    names = {a.name for a in artifacts}
    assert names == {
        "index.jsonl",
        "plans.jsonl",
        "index.md",
        "validation_report.md",
        "coverage_report.md",
        "execution_plans.md",
    }
    for art in artifacts:
        assert art.path.exists(), f"missing on disk: {art.name}"

    plans = [json.loads(line) for line in (output_dir / "plans.jsonl").read_text().splitlines()]
    by_name = {p["recipe"]: p for p in plans}
    assert by_name["release-notes"]["execution_order"] == ["collect", "summarize", "publish"]
    assert by_name["release-notes"]["acyclic"] is True

    onboard = by_name["onboard-repo"]
    assert onboard["execution_order"][0] == "map"
    assert onboard["execution_order"][-1] == "open_issue"


def test_clean_examples_have_no_errors(tmp_path: Path):
    output_dir = tmp_path / "recipe_pack"
    ctx = RunContext(job_name="recipes", output_dir=output_dir)
    RecipesPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    errors = [f for f in ctx.metadata["findings"] if f.severity == "error"]
    assert errors == [], f"clean examples produced errors: {errors}"


# ---------- validation ----------


def _parse_broken() -> list[Recipe]:
    return [parse_recipe_file(p) for p in sorted(BROKEN_DIR.glob("*.recipe.md"))]


@pytest.mark.parametrize(
    "expected_code",
    [
        "cyclic_dependency",
        "dangling_step_reference",
        "dangling_input_reference",
    ],
)
def test_validator_flags_graph_issues(expected_code: str):
    findings = validate_recipes(_parse_broken())
    codes = {f.code for f in findings}
    assert expected_code in codes, f"expected {expected_code} in {codes}"


def test_index_jsonl_pydantic_round_trip(tmp_path: Path):
    output_dir = tmp_path / "recipe_pack"
    ctx = RunContext(job_name="recipes", output_dir=output_dir)
    RecipesPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    for line in (output_dir / "index.jsonl").read_text().splitlines():
        restored = Recipe.model_validate_json(line)
        assert restored.name
        assert restored.steps
