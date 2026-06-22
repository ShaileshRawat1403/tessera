# Tessera

**One command for your repository's security and hygiene posture — in one dashboard.**

Point Tessera at a project and it detects what's there, runs the right checks, and renders everything into a single self-contained HTML report: CI security, leaked secrets, dependency drift, risky SQL migrations, Dockerfile hygiene, docs coverage, dead links, and more — 22 analyzers behind one small contract.

```bash
tessera run --input . --output run
# -> run/index.html : a browsable dashboard across every applicable check
```

No services, no API keys, no network calls, nothing executed against your code. Just static analysis turned into reviewable artifacts.

- **Status:** v0.3.1 · 259 tests · 24 packages · offline by design
- **Validated on real repos** (this monorepo + `pallets/click`) — see [docs/DOGFOODING.md](docs/DOGFOODING.md)
- **License/secret/CI/deps** checks are the headline; the rest is supporting cast

---

## Quickstart

From source (PyPI publish pending — see [docs/PUBLISHING.md](docs/PUBLISHING.md)):

```bash
git clone https://github.com/ShaileshRawat1403/tessera
cd tessera
python -m venv .venv && source .venv/bin/activate
pip install $(for p in packages/tessera-*/; do printf -- "-e %s " "$p"; done)

tessera detect --input .          # which checks apply, without running
tessera run --input . --output run
open run/index.html
```

Once published: `pip install tesserakit-app` (pulls in the whole hub).

## What it checks

Every check is a **job pack**. They group into:

**Security & secrets**
- `gha` — GitHub Actions: the `pull_request_target` + PR-checkout **RCE combo**, unpinned actions, `run:` script injection, `write-all` permissions
- `api` — curl/HTTP traces → secret-redacted surface map (secrets detected by **shape**, not just field name)
- `config` — env/config inventory + leaked-secret detection (by name *and* value shape) + drift
- `dockerfile` — image hygiene: `:latest`, root user, secrets in `ENV`, missing healthcheck

**Dependencies & licensing**
- `deps` — pinning discipline, conflicting constraints, **lockfile-vs-manifest drift**
- `license` — detect & classify the project license; flag copyleft, mismatches, missing

**Code, data & docs hygiene**
- `sql` — migration safety: `DELETE`/`UPDATE` without `WHERE`, `ADD COLUMN NOT NULL` without default, `DROP`/`TRUNCATE`
- `tests` — no-assertion tests and skipped/xfail tests that protect nothing
- `docs` — Python docstring coverage for the public API
- `links` — broken markdown links, dead anchors, orphan docs
- `todo` — `TODO`/`FIXME`/`HACK` markers → triaged backlog
- `repo` — structural map (languages, layout, manifests, signals)
- `glossary` — your codebase's **vocabulary** and where one concept is spelled inconsistently (`config`/`cfg`/`conf`)

**Specs & data**
- `openapi` — OpenAPI/Swagger lint (undeclared path params, duplicate operationIds, ...)
- `schema` — JSON Schema lint (required-not-in-properties, open objects, ...)
- `i18n` — translation-key coverage across locale files

**AI / LLM tooling**
- `evals` — messy CSV → canonical eval dataset; export to DeepEval / RAGAS / OpenAI Evals / LangSmith
- `prompts` · `skills` · `recipes` · `rag` — validate and catalog prompt files, `SKILL.md` collections, multi-step recipes, and retrieval eval sets

Full command reference: [docs/USAGE.md](docs/USAGE.md).

## How it's built

One contract, many domains. Every pack implements the same `JobPack` lifecycle:

```text
normalize  →  validate  →  generate artifacts
(messy input)  (findings)   (jsonl + markdown reports)
```

That contract **has not changed since the first commit**, yet it now carries 22 genuinely different domains — flat CSV rows, prompt files, skill folders, a recipe dependency graph, curl traces, a corpus, repo trees, env config, git history, API specs, SQL, Dockerfiles, and more. Adding a pack never touches the core.

Packs compose through **artifacts, not imports** (`tessera evals compile --from-prompts` ingests a prompts-pack output without importing it). The `tessera-app` package is a CLI-only orchestrator that runs the applicable packs and builds the dashboard — it consumes job packs but isn't one.

See [docs/architecture.md](docs/architecture.md) for the full design.

## Design principles

- **Offline & side-effect-free.** No HTTP, no LLM calls, no retrieval, no code import, no DB connection. Reading and parsing only.
- **Redaction-first.** Where secrets are involved (`api`, `config`), values are masked before they ever enter a record; a test asserts no raw secret reaches any artifact.
- **Honest about heuristics.** Lightweight parsers tuned to high-value review surfaces, tuned further against real repositories (see the dogfooding report), not just authored fixtures.
- **Tested.** 259 unit tests; every pack ships examples and round-trip tests.

## Packages & naming

24 packages: `tessera-core` (runtime + contract), `tessera-app` (orchestrator + dashboard), and 22 job packs.

> PyPI distribution names use the `tesserakit-` prefix (e.g. `pip install tesserakit-core`) because `tessera-core` was already taken. Import names stay `tessera_*` and the CLI stays `tessera` — so `tesserakit-evals` installs the `tessera_evals` package and contributes to the `tessera` CLI.

## Docs

- [Architecture](docs/architecture.md) — the JobPack contract, every pack's flow, the schema/type policy
- [Usage reference](docs/USAGE.md) — per-pack commands and options
- [Dogfooding report](docs/DOGFOODING.md) — running the hub on real repos, and the fixes it drove
- [Publishing](docs/PUBLISHING.md) — releasing to PyPI

## Status & roadmap

Three releases so far (v0.1.0 → v0.2.0 → v0.3.1). Deferred by design: live execution paths (an API caller, RAG retrieval, LLM-enriched rubrics) — these are opt-in runtime concerns that the offline canonicalization here is the foundation for.
