from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera_app.dashboard import build_dashboard
from tessera_app.detect import detect_packs
from tessera_app.markdown import render_markdown
from tessera_app.orchestrator import run_project

# The app orchestrates the other packs; skip cleanly if they aren't installed.
pytest.importorskip("tessera_repo.pack", reason="job packs not installed")
pytest.importorskip("tessera_prompts.pack", reason="job packs not installed")


def _make_project(root: Path) -> Path:
    """A small project that triggers several packs at once."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# demo\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.3.1"\ndependencies = ["rich"]\n', encoding="utf-8"
    )
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    # a prompt
    (root / "hello.prompt.md").write_text(
        "---\nname: hello\ndescription: Say hello to the user by name.\nversion: 1.0.0\n"
        "variables:\n  - name: who\n---\nHi {{who}}.\n",
        encoding="utf-8",
    )
    # a CSV for evals
    (root / "data.csv").write_text(
        "question,answer\nWhat is 2+2?,4\nCapital of France?,Paris\n", encoding="utf-8"
    )
    return root


# ---------- markdown renderer ----------


def test_markdown_headings_tables_lists_code():
    md = "# Title\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- one\n- two\n\n```\ncode\n```\n\n**bold** and `c`."
    html = render_markdown(md)
    assert "<h1>Title</h1>" in html
    assert "<table>" in html and "<th>A</th>" in html and "<td>1</td>" in html
    assert "<ul><li>one</li><li>two</li></ul>" in html
    assert "<pre class='code'>code</pre>" in html
    assert "<strong>bold</strong>" in html and "<code>c</code>" in html


def test_markdown_escapes_html():
    assert "&lt;script&gt;" in render_markdown("a <script> tag")


# ---------- detection ----------


def test_detect_multiple_packs(tmp_path: Path):
    project = _make_project(tmp_path)
    names = {d.pack for d in detect_packs(project)}
    assert {"prompts", "evals", "repo"} <= names


# ---------- orchestrator ----------


def test_run_project_runs_applicable_and_writes_manifest(tmp_path: Path):
    project = _make_project(tmp_path / "proj")
    out = tmp_path / "run"
    results = run_project(project, out)

    packs_run = {r.pack for r in results if r.ok}
    assert {"prompts", "evals", "repo"} <= packs_run

    manifest = json.loads((out / "run_manifest.json").read_text())
    assert manifest["packs"]
    # each ok pack wrote its own subdir with artifacts
    for r in results:
        if r.ok:
            assert (out / r.pack).is_dir()


def test_run_then_dashboard_is_self_contained(tmp_path: Path):
    project = _make_project(tmp_path / "proj")
    out = tmp_path / "run"
    run_project(project, out)
    html_path = build_dashboard(out)

    assert html_path.exists()
    doc = html_path.read_text(encoding="utf-8")
    assert "<title>Tessera Dashboard</title>" in doc
    assert "Tessera Dashboard" in doc
    # references the packs that ran
    assert "repo" in doc and "prompts" in doc
    # self-contained: no external script/style links
    assert "http://" not in doc and "https://" not in doc
    assert "<script" not in doc


def test_only_filter_limits_run(tmp_path: Path):
    project = _make_project(tmp_path / "proj")
    out = tmp_path / "run"
    results = run_project(project, out, only=["repo"])
    assert {r.pack for r in results} == {"repo"}
