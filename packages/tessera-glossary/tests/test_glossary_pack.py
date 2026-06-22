from __future__ import annotations

import json
from pathlib import Path

from tessera_core.models import RunContext

from tessera_glossary.pack import GlossaryPack
from tessera_glossary.schema import Term
from tessera_glossary.vocab import tokenize_identifier, words_in

REPO_ROOT = Path(__file__).resolve().parents[3]
EX = REPO_ROOT / "examples" / "glossary"


# ---------- tokenization ----------


def test_tokenize_identifier_splits_cases():
    assert tokenize_identifier("loadConfigPath") == ["load", "config", "path"]
    assert tokenize_identifier("cfg_path") == ["cfg", "path"]
    assert tokenize_identifier("RepositoryClient") == ["repository", "client"]


def test_tokenize_drops_stopwords_and_short():
    # "get", "set", "the" are stopwords; "id" too short
    assert tokenize_identifier("get_the_id") == []


def test_words_in():
    ws = words_in("The Config controls the database.")
    assert "config" in ws and "database" in ws
    assert "the" not in ws


# ---------- end-to-end ----------


def _run(tmp_path: Path):
    out = tmp_path / "glossary_pack"
    ctx = RunContext(job_name="glossary", output_dir=out)
    GlossaryPack().run(input_path=EX, ctx=ctx, options={})
    return out, ctx


def test_glossary_terms(tmp_path: Path):
    out, _ = _run(tmp_path)
    terms = {t["term"] for t in (json.loads(l) for l in (out / "glossary.jsonl").read_text().splitlines())}
    assert "config" in terms
    assert "message" in terms
    assert "repository" in terms


def test_terminology_inconsistencies(tmp_path: Path):
    out, ctx = _run(tmp_path)
    codes = {f.code for f in ctx.metadata["findings"]}
    assert "terminology_inconsistency" in codes

    inconsistencies = (out / "inconsistencies.md").read_text()
    assert "config" in inconsistencies
    # the report should list the abbreviated form too
    assert "cfg" in inconsistencies


def test_recommended_is_most_frequent(tmp_path: Path):
    _, ctx = _run(tmp_path)
    config_finding = next(
        f for f in ctx.metadata["findings"]
        if f.code == "terminology_inconsistency" and f.metadata.get("concept") == "config"
    )
    # 'config' appears more than 'cfg' in the sample -> recommended config
    assert config_finding.metadata["recommended"] == "config"


def test_artifacts(tmp_path: Path):
    out, _ = _run(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {
        "glossary.jsonl", "index.md", "validation_report.md",
        "coverage_report.md", "inconsistencies.md",
    } <= names


def test_round_trip(tmp_path: Path):
    out, _ = _run(tmp_path)
    for line in (out / "glossary.jsonl").read_text().splitlines():
        t = Term.model_validate_json(line)
        assert t.term


# ---------- precision: single-occurrence minority forms are not drift ----------
from tessera_glossary.loader import _abbreviation_clusters  # noqa: E402


def test_single_occurrence_minority_not_flagged():
    # 'button' appears, 'btn' appears once -> not a real inconsistency
    counts = {"button": 9, "btn": 1, "config": 40, "cfg": 5}
    clusters = {c["concept"] for c in _abbreviation_clusters(counts)}
    assert "button" not in clusters   # btn(1) filtered out
    assert "config" in clusters        # cfg(5) is a real minority form


def test_threshold_is_configurable():
    counts = {"config": 40, "cfg": 2}
    assert {c["concept"] for c in _abbreviation_clusters(counts, min_minority=2)} == {"config"}
    assert _abbreviation_clusters(counts, min_minority=3) == []  # cfg(2) below 3
