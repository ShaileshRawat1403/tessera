# tesserakit-rag

Compile a document corpus plus a set of queries into a validated retrieval eval dataset.

`tessera-rag` reads a directory holding a `corpus/` of documents and a `queries` file, builds a canonical `RagCase` dataset (each query with its gold retrieval target documents and optional expected answer), verifies every document reference, and emits a dataset plus reports.

## Scope (v0.1)

This pack builds and validates the dataset. It does **not** run retrieval (no embeddings, no vector store, no scoring). Like the api pack (no HTTP execution) and evals (no LLM calls), execution is a runtime concern deferred to a later version. v0.1 is the offline "is this retrieval eval set well-formed and internally consistent" pass.

## Input shape

```text
my_rag_eval/
  corpus/
    refunds.md
    billing/disputes.md
  queries.jsonl        (or queries.yaml)
```

Document ids are the corpus-relative path without suffix: `refunds`, `billing/disputes`.

Each query (one JSON object per line in `queries.jsonl`, or a YAML list):

```json
{"id": "q1", "query": "Can I get a refund after 45 days?", "expected_answer": "No, the window is 30 days.", "relevant_docs": ["refunds"], "tags": ["billing"]}
```

`relevant_docs` is the gold set the retriever should surface. `expected_answer` is optional; queries without one are flagged for human review.

## Compile a RAG eval pack

```bash
tessera rag compile --input examples/rag/ --output ./out/rag_pack
```

Artifacts written:

```text
dataset.jsonl            canonical RagCase rows (query, expected, relevant doc ids)
corpus_index.jsonl       RagDocument rows (id, title, counts, sha256)
validation_report.md     reference + hygiene findings
coverage_report.md       answer/target coverage, orphan docs, avg targets per query
retrieval_targets.md     per-query gold document set (with titles)
```

## Validation rules

- `parse_error` — a queries line/file could not be parsed
- `empty_corpus` — no documents found under `corpus/`
- `empty_document`, `duplicate_doc_id`
- `missing_query_text`, `duplicate_query`
- `dangling_doc_reference` — a query references a document not in the corpus
- `query_without_relevant_docs` — no retrieval target to score against
- `query_without_expected_answer` — needs human review
- `orphan_document` — a corpus document no query references
