from __future__ import annotations

from collections import Counter
from typing import Any

from tessera_core.models import ValidationFinding

from tessera_rag.schema import RagCase, RagDocument


def validate_rag_records(cases: list[RagCase], options: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for err in options.get("_parse_errors", []):
        findings.append(
            ValidationFinding(
                severity="error",
                code="parse_error",
                message=f"queries: {err['error']} (line {err.get('line', '?')})",
                field=None,
            )
        )

    docs: list[RagDocument] = options.get("_docs", [])
    doc_ids: set[str] = options.get("_doc_ids", set())

    if not docs:
        findings.append(
            ValidationFinding(
                severity="error", code="empty_corpus",
                message=f"no documents found under {options.get('_corpus_dir', 'corpus/')}",
                field="corpus",
            )
        )

    for d in docs:
        if d.char_count == 0:
            findings.append(
                ValidationFinding(
                    severity="warning", code="empty_document",
                    message=f"document '{d.id}' is empty", field="corpus",
                    metadata={"doc_id": d.id},
                )
            )

    dup_doc_ids = [i for i, c in Counter(d.id for d in docs).items() if c > 1]
    for did in dup_doc_ids:
        findings.append(
            ValidationFinding(
                severity="error", code="duplicate_doc_id",
                message=f"two corpus files map to the same document id '{did}'",
                field="corpus", metadata={"doc_id": did},
            )
        )

    # Query-level checks
    referenced: set[str] = set()
    seen_query_text: set[str] = set()
    for c in cases:
        def f(severity: str, code: str, message: str, field: str | None = None) -> ValidationFinding:
            return ValidationFinding(severity=severity, code=code, message=message, field=field,
                                     metadata={"id": c.id})

        if not c.query:
            findings.append(f("error", "missing_query_text", f"query '{c.id}' has no text", "query"))

        key = c.query.lower()
        if key and key in seen_query_text:
            findings.append(f("warning", "duplicate_query", f"query '{c.id}' duplicates an earlier query", "query"))
        seen_query_text.add(key)

        if not c.relevant_doc_ids:
            findings.append(f("warning", "query_without_relevant_docs",
                              f"query '{c.id}' has no relevant_docs; no retrieval target to score against", "relevant_doc_ids"))
        for ref in c.relevant_doc_ids:
            referenced.add(ref)
            if ref not in doc_ids:
                findings.append(f("error", "dangling_doc_reference",
                                  f"query '{c.id}' references unknown document '{ref}'", "relevant_doc_ids"))

        if c.review_status == "needs_human_review":
            findings.append(f("info", "query_without_expected_answer",
                              f"query '{c.id}' has no expected answer; needs human review", "expected_answer"))

    # Orphan docs: in corpus but referenced by no query
    for d in docs:
        if d.id not in referenced:
            findings.append(
                ValidationFinding(
                    severity="info", code="orphan_document",
                    message=f"document '{d.id}' is not referenced by any query", field="corpus",
                    metadata={"doc_id": d.id},
                )
            )

    return findings
