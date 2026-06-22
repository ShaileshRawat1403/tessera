# tesserakit-glossary

Extract a project's vocabulary and flag terminology drift.

`tessera-glossary` treats a codebase as a corpus. It tokenizes identifiers (splitting `snake_case`, `kebab-case`, and `camelCase`) and doc text into words, builds a frequency-ranked glossary of the project's domain terms, and — the distinctive part — detects where the **same concept is written more than one way** (`config` vs `cfg` vs `conf`, `message` vs `msg`, `repository` vs `repo`). No execution; pure static reading.

This is the project's *ubiquitous language*, surfaced and audited — something teams rarely look at directly.

## Build

```bash
tessera glossary build --input . --output ./out/glossary_pack
```

Artifacts written:

```text
glossary.jsonl           one Term per word (count, in-code, in-docs, examples)
index.md                 the top domain terms
validation_report.md     terminology-inconsistency findings
coverage_report.md       code-only vs doc-only vs shared vocabulary
inconsistencies.md       concepts written multiple ways, with a recommended form
```

## How drift is detected

A curated abbreviation map links short forms to canonical concepts (`cfg`/`conf`/`configuration` → `config`). When more than one form of a concept appears in the codebase, the concept is reported with each form's frequency and a recommended canonical spelling (the most frequent one).

## Findings

- `terminology_inconsistency` — a concept is spelled multiple ways; standardize on one
- `no_vocabulary` — nothing extracted

## Why it matters

Inconsistent vocabulary makes a codebase hard to search (`grep config` misses `cfg`), hard to read, and a sign of drifting domain understanding. The `coverage_report.md` also separates terms that appear only in code (possibly undocumented concepts) from those only in docs (possibly stale or aspirational).
