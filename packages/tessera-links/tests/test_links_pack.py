from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_links.pack import LinksPack
from tessera_links.scan import extract_links, headings_in, slugify
from tessera_links.schema import Link

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "examples" / "links" / "docs"


# ---------- primitives ----------


def test_slugify():
    assert slugify("Getting Started!") == "getting-started"
    assert slugify("Setup") == "setup"


def test_headings_in():
    slugs = headings_in(DOCS / "guide.md")
    assert "guide" in slugs and "setup" in slugs


def test_extract_links_skips_code_fence(tmp_path: Path):
    f = tmp_path / "a.md"
    f.write_text("[real](x.md)\n```\n[fake](y.md)\n```\n", encoding="utf-8")
    links = extract_links(f)
    hrefs = [h for _, _, h in links]
    assert "x.md" in hrefs
    assert "y.md" not in hrefs


# ---------- end-to-end ----------


def _run(tmp_path: Path):
    out = tmp_path / "links_pack"
    ctx = RunContext(job_name="links", output_dir=out)
    LinksPack().run(input_path=DOCS, ctx=ctx, options={})
    return out, ctx


def test_findings(tmp_path: Path):
    _, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "broken_link" in codes      # missing.md
    assert "broken_anchor" in codes     # guide.md#nope
    assert "orphan_doc" in codes        # orphan.md


def test_valid_links_not_flagged(tmp_path: Path):
    out, _ = _run(tmp_path)
    links = [json.loads(l) for l in (out / "links.jsonl").read_text().splitlines()]
    by_href = {}
    for link in links:
        by_href.setdefault(link["href"], link)
    # valid internal + valid anchor + same-file anchor must not be broken
    assert by_href["guide.md"]["broken"] is False
    assert by_href["guide.md#setup"]["broken"] is False
    assert by_href["#intro"]["broken"] is False
    # external is inventoried, classified, not broken
    assert by_href["https://example.com"]["kind"] == "external"
    assert by_href["https://example.com"]["broken"] is False


def test_broken_report_and_artifacts(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "links.jsonl", "index.md", "validation_report.md",
        "coverage_report.md", "broken.md",
    } <= names
    broken = (out / "broken.md").read_text()
    assert "missing.md" in broken
    assert "orphan.md" in broken


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "links.jsonl").read_text().splitlines():
        link = Link.model_validate_json(line)
        assert link.source_file
