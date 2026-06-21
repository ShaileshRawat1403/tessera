from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera_core.models import RunContext

from tessera_skills.deps import (
    extract_bash_commands,
    extract_mcp_tools,
    extract_skill_refs,
)
from tessera_skills.loader import discover_skill_folders, parse_skill_folder
from tessera_skills.overlap import find_overlaps, jaccard
from tessera_skills.pack import SkillsPack
from tessera_skills.schema import SkillManifest
from tessera_skills.validator import validate_skills

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "examples" / "skills"
BROKEN_DIR = Path(__file__).parent / "fixtures" / "broken"


# ---------- discovery ----------


def test_discovery_finds_each_skill_folder():
    folders = discover_skill_folders(EXAMPLES_DIR)
    names = {f.name for f in folders}
    assert names == {"changelog-generator", "pr-summary", "api-docs-check"}


def test_discovery_on_skill_md_returns_parent():
    folders = discover_skill_folders(EXAMPLES_DIR / "pr-summary" / "SKILL.md")
    assert folders == [EXAMPLES_DIR / "pr-summary"]


# ---------- parsing ----------


def test_parse_extracts_metadata_and_files():
    skill = parse_skill_folder(EXAMPLES_DIR / "changelog-generator")
    assert skill.name == "changelog-generator"
    assert skill.version == "1.0.0"
    file_kinds = {f.kind for f in skill.files}
    assert "skill" in file_kinds
    assert "script" in file_kinds


def test_parse_inventories_references_and_examples():
    skill = parse_skill_folder(EXAMPLES_DIR / "api-docs-check")
    kinds = {f.kind for f in skill.files}
    assert "reference" in kinds
    assert "example" in kinds


def test_parse_picks_up_license():
    skill = parse_skill_folder(EXAMPLES_DIR / "api-docs-check")
    assert skill.license == "MIT"


# ---------- dependency extraction ----------


def test_extract_bash_commands_picks_first_word_per_line():
    body = "```bash\ngit log --oneline\ncurl -sL example.com\n```"
    cmds = extract_bash_commands(body)
    assert "git" in cmds
    assert "curl" in cmds


def test_extract_bash_ignores_comments_and_export():
    body = "```bash\n# comment\nexport FOO=bar\ngit status\n```"
    cmds = extract_bash_commands(body)
    assert "git" in cmds
    assert "export" not in cmds


def test_extract_mcp_tools():
    body = "Uses mcp__some_server__do_thing and also mcp__other__fetch."
    tools = extract_mcp_tools(body)
    assert tools == ["mcp__other__fetch", "mcp__some_server__do_thing"]


def test_extract_skill_refs_excludes_own_name():
    body = "Compose with /changelog-generator and /pr-summary."
    refs = extract_skill_refs(body, own_name="pr-summary")
    assert refs == ["changelog-generator"]


# ---------- overlap ----------


def test_jaccard_identical_high_similarity():
    a = {"git", "commit", "release", "changelog"}
    b = {"git", "commit", "release", "changelog"}
    assert jaccard(a, b) == 1.0


def test_jaccard_disjoint_zero():
    assert jaccard({"a"}, {"b"}) == 0.0


def test_overlap_finds_designed_collision():
    skills = [parse_skill_folder(p) for p in sorted(BROKEN_DIR.iterdir()) if p.is_dir()]
    pairs = find_overlaps(skills)
    found = {(min(p.name_a, p.name_b), max(p.name_a, p.name_b)) for p in pairs}
    assert ("overlap-a", "overlap-b") in found


# ---------- end-to-end ----------


def test_pack_creates_expected_artifacts(tmp_path: Path):
    output_dir = tmp_path / "skill_pack"
    ctx = RunContext(job_name="skills", output_dir=output_dir)
    pack = SkillsPack()
    artifacts = pack.run(input_path=EXAMPLES_DIR, ctx=ctx, options={})

    names = {a.name for a in artifacts}
    assert names == {
        "index.jsonl",
        "index.md",
        "validation_report.md",
        "coverage_report.md",
        "dependencies_report.md",
    }
    for art in artifacts:
        assert art.path.exists(), f"missing on disk: {art.name}"

    index = [json.loads(line) for line in (output_dir / "index.jsonl").read_text().splitlines()]
    assert len(index) == 3
    deps_report = (output_dir / "dependencies_report.md").read_text()
    assert "git" in deps_report


def test_pack_clean_examples_have_no_errors(tmp_path: Path):
    output_dir = tmp_path / "skill_pack"
    ctx = RunContext(job_name="skills", output_dir=output_dir)
    SkillsPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    findings = ctx.metadata["findings"]
    errors = [f for f in findings if f.severity == "error"]
    assert errors == [], f"clean examples produced errors: {errors}"


# ---------- validation rules ----------


def _parse_broken_set() -> list[SkillManifest]:
    return [parse_skill_folder(p) for p in sorted(BROKEN_DIR.iterdir()) if p.is_dir()]


@pytest.mark.parametrize(
    "expected_code",
    [
        "missing_description",
        "invalid_version",
        "description_overlap_error",
    ],
)
def test_validator_flags_known_issues(expected_code: str):
    skills = _parse_broken_set()
    findings = validate_skills(skills)
    codes = {f.code for f in findings}
    assert expected_code in codes, f"expected {expected_code} in {codes}"


def test_overlap_warning_tier_fires_for_moderate_similarity():
    """Descriptions that share some topic words but not all should warn, not error."""
    from tessera_skills.schema import SkillManifest as SM

    a = SM(name="a", description="Generate changelogs from git commits grouped by type.")
    b = SM(name="b", description="Generate release notes from version tags grouped by author.")
    pairs = find_overlaps([a, b], warn_threshold=0.1, error_threshold=0.9)
    assert pairs, "expected at least one overlap pair"
    assert any(p.severity == "warning" for p in pairs)


def test_index_jsonl_pydantic_round_trip(tmp_path: Path):
    output_dir = tmp_path / "skill_pack"
    ctx = RunContext(job_name="skills", output_dir=output_dir)
    SkillsPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    for line in (output_dir / "index.jsonl").read_text().splitlines():
        restored = SkillManifest.model_validate_json(line)
        assert restored.name
        assert restored.files
