from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from tessera_glossary.schema import Term
from tessera_glossary.vocab import (
    ABBREVIATIONS,
    identifiers_in,
    tokenize_identifier,
    words_in,
)

_IGNORE = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
           "dist", "build", ".tox", "target"}
_CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".kt", ".c", ".cpp", ".cs"}
_DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt"}


def load_glossary_records(input_path: Path, options: dict[str, Any]) -> list[Term]:
    root = input_path if input_path.is_dir() else input_path.parent

    counts: dict[str, int] = defaultdict(int)
    in_code: set[str] = set()
    in_docs: set[str] = set()
    examples: dict[str, set[str]] = defaultdict(set)
    code_files = 0
    doc_files = 0

    paths = [input_path] if input_path.is_file() else [
        p for p in sorted(root.rglob("*"))
        if p.is_file() and not any(part in _IGNORE for part in p.relative_to(root).parts)
    ]

    for p in paths:
        suffix = p.suffix.lower()
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if suffix in _CODE_SUFFIXES:
            code_files += 1
            for ident in identifiers_in(text):
                for word in tokenize_identifier(ident):
                    counts[word] += 1
                    in_code.add(word)
                    if len(examples[word]) < 5:
                        examples[word].add(ident)
        elif suffix in _DOC_SUFFIXES:
            doc_files += 1
            for word in words_in(text):
                counts[word] += 1
                in_docs.add(word)

    terms = [
        Term(term=w, count=c, in_code=(w in in_code), in_docs=(w in in_docs),
             examples=sorted(examples.get(w, [])))
        for w, c in counts.items()
    ]
    terms.sort(key=lambda t: (-t.count, t.term))

    options["_code_files"] = code_files
    options["_doc_files"] = doc_files
    options["_clusters"] = _abbreviation_clusters(counts)
    options["_root"] = str(root)
    return terms


# A minority spelling must appear at least this many times to count as drift.
# Filters out single coincidental tokens (e.g. one stray `btn`) that would
# otherwise create noisy clusters on a large codebase.
MIN_MINORITY_COUNT = 2


def _abbreviation_clusters(counts: dict[str, int], min_minority: int = MIN_MINORITY_COUNT) -> list[dict[str, Any]]:
    """Group co-occurring forms that map to the same canonical concept.

    A form is kept only if it appears at least ``min_minority`` times, so a
    one-off token does not get reported as a terminology inconsistency.
    """
    by_canonical: dict[str, dict[str, int]] = defaultdict(dict)
    for word, count in counts.items():
        canon = ABBREVIATIONS.get(word)
        if canon and count >= min_minority:
            by_canonical[canon][word] = count
    clusters: list[dict[str, Any]] = []
    for canon, forms in by_canonical.items():
        if len(forms) > 1:  # more than one (non-trivial) spelling of the concept
            recommended = max(forms.items(), key=lambda kv: kv[1])[0]
            clusters.append({
                "concept": canon,
                "forms": dict(sorted(forms.items(), key=lambda kv: -kv[1])),
                "recommended": recommended,
            })
    clusters.sort(key=lambda c: -sum(c["forms"].values()))
    return clusters
