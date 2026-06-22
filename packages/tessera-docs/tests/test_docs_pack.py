from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_docs.pack import DocsPack
from tessera_docs.scan import extract_symbols, is_public
from tessera_docs.schema import DocSymbol

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE = REPO_ROOT / "examples" / "docs" / "sample"


def _run(tmp_path: Path):
    out = tmp_path / "docs_pack"
    ctx = RunContext(job_name="docs", output_dir=out)
    DocsPack().run(input_path=SAMPLE, ctx=ctx, options={})
    return out, ctx


# ---------- primitives ----------


def test_is_public():
    assert is_public("add")
    assert not is_public("_helper")
    assert not is_public("__init__")


def test_extract_symbols_documented(tmp_path: Path):
    syms, err = extract_symbols(SAMPLE, SAMPLE / "documented.py")
    assert err is None
    by_qual = {s.qualname: s for s in syms}
    # module symbol has empty qualname
    assert by_qual[""].kind == "module" and by_qual[""].has_docstring
    assert by_qual["add"].has_docstring
    assert by_qual["Calculator"].has_docstring
    assert by_qual["Calculator.total"].kind == "method" and by_qual["Calculator.total"].has_docstring


def test_extract_symbols_undocumented(tmp_path: Path):
    syms, _ = extract_symbols(SAMPLE, SAMPLE / "undocumented.py")
    by_qual = {s.qualname: s for s in syms}
    assert not by_qual[""].has_docstring                 # no module docstring
    assert not by_qual["subtract"].has_docstring
    assert not by_qual["Widget.render"].has_docstring
    assert by_qual["Widget._private_helper"].is_public is False


# ---------- end-to-end ----------


def test_pack_artifacts_and_coverage(tmp_path: Path):
    out, ctx = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "symbols.jsonl", "index.md", "validation_report.md",
        "coverage_report.md", "undocumented.md",
    } <= names

    index = (out / "index.md").read_text()
    assert "Coverage:" in index

    # undocumented.md should list the undocumented public symbols
    undoc = (out / "undocumented.md").read_text()
    assert "subtract" in undoc
    assert "Widget.render" in undoc
    # private helper must NOT be listed
    assert "_private_helper" not in undoc


def test_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "missing_function_docstring" in codes   # subtract
    assert "missing_method_docstring" in codes      # Widget.render
    assert "missing_module_docstring" in codes      # undocumented.py
    assert "low_doc_coverage" in codes              # half the sample is undocumented


def test_symbols_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "symbols.jsonl").read_text().splitlines():
        s = DocSymbol.model_validate_json(line)
        assert s.kind in ("module", "class", "function", "method")
