from __future__ import annotations

import hashlib
import re
from pathlib import Path

from tessera_rag.schema import RagDocument

CORPUS_DIRNAME = "corpus"
DOC_SUFFIXES = {".md", ".txt", ".markdown", ".rst"}

_H1_RE = re.compile(r"^\s*#\s+(.+)$", re.MULTILINE)


def doc_id_for(rel: Path) -> str:
    """Corpus-relative path without suffix, POSIX-style: 'billing/disputes'."""
    return rel.with_suffix("").as_posix()


def load_corpus(corpus_dir: Path) -> list[RagDocument]:
    docs: list[RagDocument] = []
    if not corpus_dir.exists():
        return docs
    for path in sorted(corpus_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in DOC_SUFFIXES:
            continue
        rel = path.relative_to(corpus_dir)
        text = path.read_text(encoding="utf-8")
        words = text.split()
        title = ""
        m = _H1_RE.search(text)
        if m:
            title = m.group(1).strip()
        docs.append(
            RagDocument(
                id=doc_id_for(rel),
                path=str(path),
                title=title or rel.stem,
                char_count=len(text),
                word_count=len(words),
                sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )
        )
    return docs
