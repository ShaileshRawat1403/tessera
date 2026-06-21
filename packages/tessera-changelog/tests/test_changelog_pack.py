from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tessera_core.models import RunContext

from tessera_changelog.conventional import parse_subject
from tessera_changelog.pack import ChangelogPack
from tessera_changelog.schema import Commit

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples" / "changelog"


# ---------- conventional parsing ----------


def test_parse_feat_with_scope():
    p = parse_subject("feat(evals): add scoring")
    assert p["type"] == "feat"
    assert p["scope"] == "evals"
    assert p["conventional"] is True
    assert p["breaking"] is False


def test_parse_breaking_bang():
    p = parse_subject("refactor!: rename things")
    assert p["type"] == "refactor"
    assert p["breaking"] is True


def test_parse_breaking_body_trailer():
    p = parse_subject("feat: x", body="BREAKING CHANGE: y")
    assert p["breaking"] is True


def test_parse_non_conventional():
    p = parse_subject("updated some stuff")
    assert p["type"] == "other"
    assert p["conventional"] is False


def test_parse_pr_number():
    p = parse_subject("fix: thing (#42)")
    assert p["pr_number"] == "42"


# ---------- end-to-end (jsonl source) ----------


def test_pack_from_jsonl(tmp_path: Path):
    out = tmp_path / "cl"
    ctx = RunContext(job_name="changelog", output_dir=out)
    artifacts = ChangelogPack().run(input_path=EXAMPLES, ctx=ctx, options={})

    names = {a.name for a in artifacts}
    assert names == {
        "commits.jsonl",
        "CHANGELOG.md",
        "release_notes.md",
        "validation_report.md",
        "coverage_report.md",
    }

    changelog = (out / "CHANGELOG.md").read_text()
    assert "## Features" in changelog
    assert "## Fixes" in changelog
    assert "## Breaking Changes" in changelog
    assert "column confidence scoring" in changelog

    codes = {f.code for f in ctx.metadata["findings"]}
    assert "wip_commit" in codes              # the "wip: ..." commit
    assert "non_conventional_commit" in codes  # "updated some stuff"
    assert "breaking_change" in codes          # the refactor! commit


def test_release_notes_counts(tmp_path: Path):
    out = tmp_path / "cl"
    ctx = RunContext(job_name="changelog", output_dir=out)
    ChangelogPack().run(input_path=EXAMPLES, ctx=ctx, options={})
    notes = (out / "release_notes.md").read_text()
    assert "2 features" in notes
    assert "breaking changes" in notes


def test_commits_jsonl_round_trip(tmp_path: Path):
    out = tmp_path / "cl"
    ctx = RunContext(job_name="changelog", output_dir=out)
    ChangelogPack().run(input_path=EXAMPLES, ctx=ctx, options={})
    for line in (out / "commits.jsonl").read_text().splitlines():
        restored = Commit.model_validate_json(line)
        assert restored.subject


# ---------- git source (skipped if git unavailable) ----------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_pack_from_real_git_repo(tmp_path: Path):
    if not _has_git():
        pytest.skip("git not available")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "a.txt").write_text("1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: first feature")
    (repo / "a.txt").write_text("2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fix: a bug")

    out = tmp_path / "cl"
    ctx = RunContext(job_name="changelog", output_dir=out)
    ChangelogPack().run(input_path=repo, ctx=ctx, options={})

    assert ctx.metadata["record_count"] == 2
    changelog = (out / "CHANGELOG.md").read_text()
    assert "first feature" in changelog and "a bug" in changelog


def _has_git() -> bool:
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
        return True
    except Exception:
        return False
