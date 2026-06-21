from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_repo.languages import kind_for, language_for
from tessera_repo.manifests import detect_and_parse
from tessera_repo.pack import RepoPack
from tessera_repo.scanner import scan_repo
from tessera_repo.schema import RepoFile

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE = REPO_ROOT / "examples" / "repo" / "sample"


# ---------- classification ----------


def test_language_detection():
    assert language_for(Path("a/b.py")) == "Python"
    assert language_for(Path("x.ts")) == "TypeScript"
    assert language_for(Path("notes.md")) == "Markdown"


def test_kind_detection():
    assert kind_for(Path("src/calc/__init__.py")) == "source"
    assert kind_for(Path("tests/test_calc.py")) == "test"
    assert kind_for(Path("pyproject.toml")) == "build"
    assert kind_for(Path("README.md")) == "docs"


# ---------- manifest parsing ----------


def test_pyproject_dependency_parse():
    man = detect_and_parse(SAMPLE, Path("pyproject.toml"))
    assert man is not None
    assert man.kind == "pyproject"
    assert "rich" in man.dependencies
    assert "typer" in man.dependencies


# ---------- scanning ----------


def test_scan_ignores_build_dirs(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "junk.py").write_text("x=1\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("module.exports={}\n")

    files, _manifests, _signals = scan_repo(tmp_path)
    paths = {f.path for f in files}
    assert "src/main.py" in paths
    assert not any(".venv" in p or "node_modules" in p for p in paths)


def test_signals_on_sample():
    _files, manifests, signals = scan_repo(SAMPLE)
    assert signals["has_readme"] is True
    assert signals["has_tests"] is True
    assert any(m.kind == "pyproject" for m in manifests)


# ---------- end-to-end ----------


def test_pack_creates_expected_artifacts(tmp_path: Path):
    out = tmp_path / "repo_pack"
    ctx = RunContext(job_name="repo", output_dir=out)
    artifacts = RepoPack().run(input_path=SAMPLE, ctx=ctx, options={})

    names = {a.name for a in artifacts}
    assert names == {
        "files.jsonl",
        "repo_map.json",
        "index.md",
        "validation_report.md",
        "coverage_report.md",
        "dependencies_report.md",
    }
    for a in artifacts:
        assert a.path.exists()

    repo_map = json.loads((out / "repo_map.json").read_text())
    assert repo_map["languages"].get("Python", 0) >= 2
    assert repo_map["signals"]["has_tests"] is True

    deps = (out / "dependencies_report.md").read_text()
    assert "rich" in deps and "typer" in deps


def test_sample_repo_has_no_errors(tmp_path: Path):
    out = tmp_path / "repo_pack"
    ctx = RunContext(job_name="repo", output_dir=out)
    RepoPack().run(input_path=SAMPLE, ctx=ctx, options={})
    errors = [f for f in ctx.metadata["findings"] if f.severity == "error"]
    assert errors == []


def test_missing_readme_and_tests_flagged(tmp_path: Path):
    (tmp_path / "main.py").write_text("x = 1\n")
    out = tmp_path / "repo_pack"
    ctx = RunContext(job_name="repo", output_dir=out)
    RepoPack().run(input_path=tmp_path, ctx=ctx, options={})
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "missing_readme" in codes
    assert "no_tests_detected" in codes


def test_files_jsonl_pydantic_round_trip(tmp_path: Path):
    out = tmp_path / "repo_pack"
    ctx = RunContext(job_name="repo", output_dir=out)
    RepoPack().run(input_path=SAMPLE, ctx=ctx, options={})
    for line in (out / "files.jsonl").read_text().splitlines():
        restored = RepoFile.model_validate_json(line)
        assert restored.path
