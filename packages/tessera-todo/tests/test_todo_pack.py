from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_todo.pack import TodoPack
from tessera_todo.scan import scan_todos
from tessera_todo.schema import TodoItem

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DIR = REPO_ROOT / "examples" / "todo"


# ---------- scanning ----------


def test_scan_finds_markers():
    items, files = scan_todos(SAMPLE_DIR)
    assert files >= 1
    markers = [it.marker for it in items]
    assert "TODO" in markers
    assert "FIXME" in markers
    assert "HACK" in markers
    assert "NOTE" in markers


def test_owner_and_priority():
    items, _ = scan_todos(SAMPLE_DIR)
    todo_sam = next(it for it in items if it.marker == "TODO" and it.owner == "sam")
    assert "refactor" in todo_sam.text.lower()
    assert todo_sam.priority == "normal"

    fixme = next(it for it in items if it.marker == "FIXME")
    assert fixme.priority == "high"

    note = next(it for it in items if it.marker == "NOTE")
    assert note.priority == "low"


def test_hack_without_colon_has_text():
    items, _ = scan_todos(SAMPLE_DIR)
    hack = next(it for it in items if it.marker == "HACK")
    assert "shim" in hack.text.lower()


# ---------- end-to-end ----------


def _run(tmp_path: Path):
    out = tmp_path / "todo_pack"
    ctx = RunContext(job_name="todo", output_dir=out)
    TodoPack().run(input_path=SAMPLE_DIR, ctx=ctx, options={})
    return out, ctx


def test_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "high_priority_marker" in codes   # FIXME / HACK
    assert "todo_without_owner" in codes      # the bare TODO
    assert "marker_without_text" in codes     # the bare TODO


def test_artifacts_and_by_owner(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "todos.jsonl", "index.md", "validation_report.md",
        "coverage_report.md", "by_owner.md",
    } <= names
    by_owner = (out / "by_owner.md").read_text()
    assert "sam" in by_owner
    assert "(unassigned)" in by_owner


def test_index_orders_high_priority_first(tmp_path: Path):
    out, _ = _run(tmp_path)
    index = (out / "index.md").read_text()
    # the first data row in the table should be a high-priority marker
    rows = [ln for ln in index.splitlines() if ln.startswith("| ") and "Priority" not in ln and "---" not in ln]
    assert rows, "expected backlog rows"
    assert rows[0].split("|")[1].strip() == "high"


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "todos.jsonl").read_text().splitlines():
        it = TodoItem.model_validate_json(line)
        assert it.marker
