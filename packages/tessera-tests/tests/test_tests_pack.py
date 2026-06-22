from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_tests.pack import TestsPack
from tessera_tests.scan import extract_tests, is_test_file
from tessera_tests.schema import TestCase

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE = REPO_ROOT / "examples" / "tests"
SAMPLE_FILE = SAMPLE / "sample" / "test_sample.py"


# ---------- discovery / extraction ----------


def test_is_test_file():
    assert is_test_file(Path("tests/test_x.py"))
    assert is_test_file(Path("foo_test.py"))
    assert not is_test_file(Path("src/app.py"))


def test_extract_flags():
    cases, err = extract_tests(SAMPLE, SAMPLE_FILE)
    assert err is None
    by = {c.qualname: c for c in cases}

    assert by["test_passes_with_assert"].has_assert
    assert by["test_no_assertions"].has_assert is False
    assert by["test_skipped"].is_skipped
    assert by["test_expected_fail"].is_xfail
    assert by["test_parametrized"].is_parametrized and by["test_parametrized"].has_assert
    assert by["TestThing.test_method_with_assert"].kind == "method"
    assert by["TestThing.test_method_with_assert"].has_assert  # self.assertEqual


# ---------- end-to-end ----------


def _run(tmp_path: Path):
    out = tmp_path / "tests_pack"
    ctx = RunContext(job_name="tests", output_dir=out)
    TestsPack().run(input_path=SAMPLE, ctx=ctx, options={})
    return out, ctx


def test_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "no_assertion_test" in codes   # test_no_assertions
    assert "skipped_test" in codes
    assert "xfail_test" in codes


def test_no_assertion_excludes_skipped(tmp_path: Path):
    """A skipped test with no real assertion must not be double-flagged as no_assertion."""
    _, ctx = _run(tmp_path)
    no_assert = [f for f in ctx.metadata["findings"] if f.code == "no_assertion_test"]
    flagged = {f.metadata.get("name") for f in no_assert}
    assert "test_skipped" not in flagged
    assert "test_no_assertions" in flagged


def test_artifacts_and_not_running(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "tests.jsonl", "index.md", "validation_report.md",
        "coverage_report.md", "not_running.md",
    } <= names
    not_running = (out / "not_running.md").read_text()
    assert "test_skipped" in not_running
    assert "test_expected_fail" in not_running


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "tests.jsonl").read_text().splitlines():
        c = TestCase.model_validate_json(line)
        assert c.name
