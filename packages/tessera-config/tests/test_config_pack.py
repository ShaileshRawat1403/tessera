from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_config.envparse import parse_env
from tessera_config.pack import ConfigPack
from tessera_config.redact import is_secret_name, mask
from tessera_config.scan import find_code_references, find_env_files
from tessera_config.schema import ConfigKey

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples" / "config"

RAW_TOKEN = "DEMO_NOT_A_REAL_TOKEN_abcdef0123456789"


# ---------- primitives ----------


def test_mask_hides_tail():
    out = mask("abcdef123456")
    assert out.startswith("ab")
    assert "123456" not in out
    assert "len=12" in out


def test_secret_name_detection():
    assert is_secret_name("API_TOKEN")
    assert is_secret_name("DB_PASSWORD")
    assert not is_secret_name("APP_PORT")


def test_env_parse(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text('export A=1\nB="two"\n# c\nC=three # inline\n', encoding="utf-8")
    parsed = parse_env(p)
    assert parsed == {"A": "1", "B": "two", "C": "three"}


# ---------- scanning ----------


def test_find_env_files_classifies_real_vs_example():
    real, example = find_env_files(EXAMPLES)
    real_names = {p.name for p in real}
    example_names = {p.name for p in example}
    assert ".env" in real_names
    assert ".env.example" in example_names


def test_find_code_references():
    refs = find_code_references(EXAMPLES)
    assert "APP_PORT" in refs
    assert "API_TOKEN" in refs
    assert "CACHE_TTL" in refs


# ---------- end-to-end ----------


def _run(tmp_path: Path) -> tuple[Path, RunContext]:
    out = tmp_path / "config_pack"
    ctx = RunContext(job_name="config", output_dir=out)
    ConfigPack().run(input_path=EXAMPLES, ctx=ctx, options={})
    return out, ctx


def test_inventory_and_flags(tmp_path: Path):
    out, _ = _run(tmp_path)
    rows = {r["name"]: r for r in (json.loads(l) for l in (out / "config_inventory.jsonl").read_text().splitlines())}

    assert rows["APP_PORT"]["in_env"] and rows["APP_PORT"]["in_example"] and rows["APP_PORT"]["in_code"]
    assert rows["API_TOKEN"]["is_secret"] is True
    assert rows["LEGACY_DEBUG"]["in_env"] and not rows["LEGACY_DEBUG"]["in_example"]
    assert rows["CACHE_TTL"]["in_code"] and not rows["CACHE_TTL"]["in_example"]
    assert rows["FEATURE_FLAG_X"]["in_example"] and not rows["FEATURE_FLAG_X"]["in_code"]


def test_findings_cover_secret_and_drift(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "possible_committed_secret" in codes  # API_TOKEN
    assert "missing_in_example" in codes         # CACHE_TTL
    assert "undocumented_env_key" in codes       # LEGACY_DEBUG
    assert "unused_documented_key" in codes      # FEATURE_FLAG_X


def test_no_raw_secret_in_any_artifact(tmp_path: Path):
    out, _ = _run(tmp_path)
    for artifact_file in out.iterdir():
        content = artifact_file.read_text(encoding="utf-8")
        assert RAW_TOKEN not in content, f"raw token leaked into {artifact_file.name}"


def test_drift_report_sections(tmp_path: Path):
    out, _ = _run(tmp_path)
    drift = (out / "drift_report.md").read_text()
    assert "Used in code but undocumented" in drift
    assert "CACHE_TTL" in drift
    assert "FEATURE_FLAG_X" in drift


def test_inventory_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "config_inventory.jsonl").read_text().splitlines():
        restored = ConfigKey.model_validate_json(line)
        assert restored.name


# ---------- v0.2: shape-based secret detection in values ----------
from tessera_config.redact import detect_secret_shape  # noqa: E402

_GH = "ghp_" + "A1b2C3d4" * 5  # constructed at runtime; not a committed literal


def test_detect_secret_shape():
    assert detect_secret_shape(_GH) == "github_token"
    assert detect_secret_shape("8080") is None
    assert detect_secret_shape("postgres://u@localhost/db") is None


def test_secret_value_in_nonsecret_key(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    # key name is innocuous, but the VALUE is a token
    (proj / ".env").write_text(f"WIDGET_ENDPOINT={_GH}\nAPP_PORT=8080\n", encoding="utf-8")
    out = tmp_path / "config_pack"
    ctx = RunContext(job_name="config", output_dir=out)
    ConfigPack().run(input_path=proj, ctx=ctx, options={})
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "secret_value_in_nonsecret_key" in codes
    # the raw token must not leak into any artifact
    for artifact_file in out.iterdir():
        assert _GH not in artifact_file.read_text(encoding="utf-8")
