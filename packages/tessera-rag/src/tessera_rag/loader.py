from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from tessera_rag.corpus import CORPUS_DIRNAME, load_corpus
from tessera_rag.schema import RagCase, RagDocument, RagQuery

QUERY_FILENAMES = ("queries.jsonl", "queries.yaml", "queries.yml")


def _find_queries_file(root: Path) -> Path | None:
    for name in QUERY_FILENAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def _load_query_specs(path: Path, parse_errors: list[dict[str, str]]) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                parse_errors.append({"line": str(lineno), "error": str(exc)})
        return rows
    # yaml / yml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if isinstance(data, dict) and "queries" in data:
        data = data["queries"]
    if not isinstance(data, list):
        parse_errors.append({"line": "-", "error": "queries file is not a list"})
        return []
    return [d for d in data if isinstance(d, dict)]


def _coerce_query(raw: dict[str, Any], idx: int) -> RagQuery:
    rel = raw.get("relevant_docs", []) or raw.get("relevant_doc_ids", []) or []
    if isinstance(rel, str):
        rel = [rel]
    return RagQuery(
        id=str(raw.get("id") or f"q{idx}"),
        query=str(raw.get("query", "") or raw.get("question", "")),
        expected_answer=str(raw.get("expected_answer", "") or raw.get("expected", "")),
        relevant_docs=[str(d) for d in rel],
        tags=list(raw.get("tags", []) or []),
    )


def load_rag_records(input_path: Path, options: dict[str, Any]) -> list[RagCase]:
    """Load a corpus + queries directory into canonical RagCase records.

    Stashes the corpus, raw queries, and parse errors in ``options`` so the
    validate and write steps can reuse them.
    """
    root = input_path if input_path.is_dir() else input_path.parent
    corpus_dir = root / CORPUS_DIRNAME
    docs: list[RagDocument] = load_corpus(corpus_dir)
    doc_ids = {d.id for d in docs}

    parse_errors: list[dict[str, str]] = []
    queries_file = _find_queries_file(root)
    raw_specs: list[dict[str, Any]] = []
    if queries_file is None:
        parse_errors.append({"line": "-", "error": f"no queries file found in {root} (expected one of {', '.join(QUERY_FILENAMES)})"})
    else:
        raw_specs = _load_query_specs(queries_file, parse_errors)

    queries = [_coerce_query(r, i) for i, r in enumerate(raw_specs, start=1)]

    cases: list[RagCase] = []
    for q in queries:
        review_status = "source_extracted" if q.expected_answer.strip() else "needs_human_review"
        cases.append(
            RagCase(
                id=q.id,
                query=q.query.strip(),
                expected_answer=q.expected_answer.strip(),
                relevant_doc_ids=q.relevant_docs,
                review_status=review_status,
                tags=q.tags,
                metadata={"source_queries_file": str(queries_file) if queries_file else ""},
            )
        )

    options["_docs"] = docs
    options["_doc_ids"] = doc_ids
    options["_queries"] = queries
    options["_parse_errors"] = parse_errors
    options["_corpus_dir"] = str(corpus_dir)
    return cases
