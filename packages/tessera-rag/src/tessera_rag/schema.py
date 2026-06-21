from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RagDocument(BaseModel):
    """A corpus document. Serialized to ``corpus_index.jsonl``."""

    id: str  # corpus-relative path without suffix, e.g. "billing/disputes"
    path: str  # source path
    title: str = ""
    char_count: int = 0
    word_count: int = 0
    sha256: str = ""
    tags: list[str] = Field(default_factory=list)


class RagQuery(BaseModel):
    """A raw query spec as authored in the queries file."""

    id: str
    query: str
    expected_answer: str = ""
    relevant_docs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RagCase(BaseModel):
    """Canonical retrieval eval record. Serialized to ``dataset.jsonl``.

    ``relevant_doc_ids`` is the gold retrieval target set: the documents a
    retriever should surface for this query. v0.1 does not run retrieval; this
    is the validated dataset a retriever would be evaluated against.
    """

    id: str
    query: str
    expected_answer: str = ""
    relevant_doc_ids: list[str] = Field(default_factory=list)
    review_status: str = "source_extracted"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
