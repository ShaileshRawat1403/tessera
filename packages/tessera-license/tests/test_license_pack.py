from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_license.detect import category_for, detect_from_text, normalize_declared
from tessera_license.pack import LicensePack
from tessera_license.schema import LicenseFinding

REPO_ROOT = Path(__file__).resolve().parents[3]
EX = REPO_ROOT / "examples" / "license"

GPL_TEXT = "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n..."
APACHE_TEXT = "Apache License\nVersion 2.0, January 2004\n..."


# ---------- detection ----------


def test_detect_from_text():
    assert detect_from_text((EX / "LICENSE").read_text()) == "MIT"
    assert detect_from_text(GPL_TEXT) == "GPL-3.0"
    assert detect_from_text(APACHE_TEXT) == "Apache-2.0"
    assert detect_from_text("totally unknown blob") == "unknown"


def test_normalize_declared():
    assert normalize_declared("MIT") == "MIT"
    assert normalize_declared("Apache-2.0") == "Apache-2.0"
    assert normalize_declared("GPL-3.0-only") == "GPL-3.0"


def test_category():
    assert category_for("MIT") == "permissive"
    assert category_for("GPL-3.0") == "copyleft"
    assert category_for("MPL-2.0") == "weak-copyleft"


# ---------- end-to-end ----------


def _run(tmp_path: Path, target: Path):
    out = tmp_path / "license_pack"
    ctx = RunContext(job_name="license", output_dir=out)
    LicensePack().run(input_path=target, ctx=ctx, options={})
    return out, ctx


def test_clean_mit_project(tmp_path: Path):
    out, ctx = _run(tmp_path, EX)
    records = [json.loads(l) for l in (out / "licenses.jsonl").read_text().splitlines()]
    ids = {r["license_id"] for r in records}
    assert "MIT" in ids
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "copyleft_license" not in codes
    assert "missing_license_file" not in codes
    assert "license_mismatch" not in codes


def test_copyleft_flagged(tmp_path: Path):
    proj = tmp_path / "gplproj"
    proj.mkdir()
    (proj / "LICENSE").write_text(GPL_TEXT, encoding="utf-8")
    out, ctx = _run(tmp_path, proj)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "copyleft_license" in codes


def test_missing_license_file(tmp_path: Path):
    proj = tmp_path / "nofile"
    proj.mkdir()
    (proj / "package.json").write_text('{"name":"x","license":"MIT"}', encoding="utf-8")
    out, ctx = _run(tmp_path, proj)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "missing_license_file" in codes


def test_license_mismatch(tmp_path: Path):
    proj = tmp_path / "mismatch"
    proj.mkdir()
    (proj / "LICENSE").write_text((EX / "LICENSE").read_text(), encoding="utf-8")   # MIT
    (proj / "pyproject.toml").write_text('[project]\nname="x"\nversion="0.1.0"\nlicense = "Apache-2.0"\n', encoding="utf-8")
    out, ctx = _run(tmp_path, proj)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "license_mismatch" in codes


def test_no_license(tmp_path: Path):
    proj = tmp_path / "bare"
    proj.mkdir()
    (proj / "main.py").write_text("x = 1\n", encoding="utf-8")
    out, ctx = _run(tmp_path, proj)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "no_license" in codes


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path, EX)
    for line in (out / "licenses.jsonl").read_text().splitlines():
        r = LicenseFinding.model_validate_json(line)
        assert r.source
