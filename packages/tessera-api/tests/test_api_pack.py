from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_api.curl import parse_curl, split_curl_commands
from tessera_api.pack import ApiPack
from tessera_api.redact import mask
from tessera_api.schema import ApiRequest
from tessera_api.validator import validate_api_records

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "examples" / "api"
FIXTURES = Path(__file__).parent / "fixtures"

# Raw secret strings that must NEVER appear in any artifact. These are fake,
# non-functional demo values chosen to match no real provider key format.
LIVE_SECRET = "DEMOBEARERtokenABCDEFGHIJKLMNOPQRSTUVWXYZ01"
API_KEY = "DEMOAPIKEYabcdef0123456789"
QUERY_SECRET = "legacy_secret_key_998877"
BASIC_PASS = "hunter2"
BODY_PASS = "s3cr3t-p@ss"
ALL_SECRETS = [LIVE_SECRET, API_KEY, QUERY_SECRET, BASIC_PASS, BODY_PASS]


# ---------- mask primitive ----------


def test_mask_never_reveals_tail():
    out = mask("supersecrettoken", lead=2)
    assert out.startswith("su")
    assert "token" not in out
    assert "len=16" in out


def test_mask_short_value():
    assert "redacted" in mask("ab")


# ---------- splitting ----------


def test_split_multiple_commands():
    text = (EXAMPLES_DIR / "payments.curl").read_text()
    cmds = split_curl_commands(text)
    assert len(cmds) == 3
    assert all(c.startswith("curl") for c in cmds)


def test_split_joins_line_continuations():
    text = "curl https://x.test/a \\\n  -H 'Accept: application/json'"
    cmds = split_curl_commands(text)
    assert len(cmds) == 1
    assert "Accept" in cmds[0]


# ---------- parsing + redaction ----------


def test_bearer_token_redacted_and_auth_detected():
    cmd = f'curl -X GET https://api.test/v1/x -H "Authorization: Bearer {LIVE_SECRET}"'
    r = parse_curl(cmd, "r1")
    assert r.method == "GET"
    assert r.auth.kind == "bearer"
    assert r.auth.present
    assert r.headers["Authorization"] == "(redacted)"
    assert LIVE_SECRET not in json.dumps(r.model_dump())
    assert any(red.kind == "bearer_token" for red in r.redactions)


def test_api_key_header_redacted():
    cmd = f'curl https://api.test/v1/x -H "X-Api-Key: {API_KEY}"'
    r = parse_curl(cmd, "r1")
    assert r.auth.kind == "api_key_header"
    assert API_KEY not in json.dumps(r.model_dump())


def test_secret_in_query_redacted_and_auth_inferred():
    cmd = f'curl "https://api.test/report?api_key={QUERY_SECRET}&format=csv"'
    r = parse_curl(cmd, "r1")
    assert r.query["api_key"] == "(redacted)"
    assert r.query["format"] == "csv"
    assert QUERY_SECRET not in r.url
    assert QUERY_SECRET not in json.dumps(r.model_dump())
    assert r.auth.kind == "api_key_query"


def test_basic_auth_flag_redacted():
    cmd = f"curl -u admin:{BASIC_PASS} https://api.test/admin"
    r = parse_curl(cmd, "r1")
    assert r.auth.kind == "basic"
    assert BASIC_PASS not in json.dumps(r.model_dump())


def test_body_secret_redacted():
    cmd = 'curl -X POST https://api.test/login -d \'{"username": "ops", "password": "s3cr3t-p@ss"}\''
    r = parse_curl(cmd, "r1")
    assert r.method == "POST"
    assert BODY_PASS not in (r.body or "")
    assert "ops" in (r.body or "")  # non-secret field preserved


def test_method_defaults_to_post_when_body_present():
    r = parse_curl('curl https://api.test/x -d \'{"a":1}\'', "r1")
    assert r.method == "POST"


def test_no_url_raises():
    import pytest

    with pytest.raises(ValueError):
        parse_curl('curl -X POST -H "Accept: application/json"', "r1")


# ---------- end-to-end ----------


def test_pack_creates_expected_artifacts(tmp_path: Path):
    out = tmp_path / "api_pack"
    ctx = RunContext(job_name="api", output_dir=out)
    artifacts = ApiPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})

    names = {a.name for a in artifacts}
    assert names == {
        "index.jsonl",
        "index.md",
        "validation_report.md",
        "coverage_report.md",
        "redactions_report.md",
    }
    for art in artifacts:
        assert art.path.exists()


def test_no_secret_leaks_into_any_artifact(tmp_path: Path):
    """The headline safety guarantee: no raw secret appears in any output file."""
    out = tmp_path / "api_pack"
    ctx = RunContext(job_name="api", output_dir=out)
    ApiPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})

    for artifact_file in out.iterdir():
        content = artifact_file.read_text(encoding="utf-8")
        for secret in ALL_SECRETS:
            assert secret not in content, f"{secret!r} leaked into {artifact_file.name}"


def test_redactions_report_lists_every_secret(tmp_path: Path):
    out = tmp_path / "api_pack"
    ctx = RunContext(job_name="api", output_dir=out)
    ApiPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    report = (out / "redactions_report.md").read_text()
    assert "bearer_token" in report
    assert "api_key" in report
    assert "basic_credentials" in report


def test_validation_flags_http_and_query_secret(tmp_path: Path):
    out = tmp_path / "api_pack"
    ctx = RunContext(job_name="api", output_dir=out)
    ApiPack().run(input_path=EXAMPLES_DIR / "legacy.curl", ctx=ctx, options={})
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "insecure_scheme" in codes
    assert "secret_in_url_query" in codes


def test_parse_error_surfaced(tmp_path: Path):
    out = tmp_path / "api_pack"
    ctx = RunContext(job_name="api", output_dir=out)
    ApiPack().run(input_path=FIXTURES / "unparseable.curl", ctx=ctx, options={})
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "parse_error" in codes


def test_index_jsonl_pydantic_round_trip(tmp_path: Path):
    out = tmp_path / "api_pack"
    ctx = RunContext(job_name="api", output_dir=out)
    ApiPack().run(input_path=EXAMPLES_DIR, ctx=ctx, options={})
    for line in (out / "index.jsonl").read_text().splitlines():
        restored = ApiRequest.model_validate_json(line)
        assert restored.id
        assert restored.method


def test_duplicate_request_detected():
    cmd = "curl https://api.test/same"
    r1 = parse_curl(cmd, "a")
    r2 = parse_curl(cmd, "b")
    findings = validate_api_records([r1, r2])
    assert any(f.code == "duplicate_request" for f in findings)
