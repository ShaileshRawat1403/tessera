from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_i18n.loader import flatten
from tessera_i18n.pack import I18nPack
from tessera_i18n.schema import LocaleFile

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCALES = REPO_ROOT / "examples" / "i18n" / "locales"


# ---------- flatten ----------


def test_flatten_nested():
    flat = flatten({"a": "1", "b": {"c": "2", "d": {"e": "3"}}})
    assert flat == {"a": "1", "b.c": "2", "b.d.e": "3"}


def test_flatten_empty_value():
    flat = flatten({"x": "", "y": None})
    assert flat["x"] == ""
    assert flat["y"] == ""


# ---------- end-to-end ----------


def _run(tmp_path: Path):
    out = tmp_path / "i18n_pack"
    ctx = RunContext(job_name="i18n", output_dir=out)
    I18nPack().run(input_path=LOCALES, ctx=ctx, options={})
    return out, ctx


def test_reference_and_coverage(tmp_path: Path):
    out, ctx = _run(tmp_path)
    locs = {l["locale"]: l for l in (json.loads(x) for x in (out / "locales.jsonl").read_text().splitlines())}
    assert locs["en"]["is_reference"] is True
    # fr is missing menu.edit -> 3/4 = 75%
    assert locs["fr"]["coverage"] == 0.75
    assert "menu.edit" in locs["fr"]["missing_keys"]
    assert "farewell" in locs["fr"]["empty_keys"]
    # es has all reference keys + an extra
    assert locs["es"]["coverage"] == 1.0
    assert "legacy_key" in locs["es"]["extra_keys"]


def test_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "missing_translations" in codes   # fr
    assert "low_coverage" in codes            # fr 75%
    assert "empty_values" in codes            # fr farewell
    assert "extra_keys" in codes              # es legacy_key


def test_artifacts_and_missing_report(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "locales.jsonl", "index.md", "validation_report.md",
        "coverage_report.md", "missing_keys.md",
    } <= names
    missing = (out / "missing_keys.md").read_text()
    assert "menu.edit" in missing


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "locales.jsonl").read_text().splitlines():
        loc = LocaleFile.model_validate_json(line)
        assert loc.locale
