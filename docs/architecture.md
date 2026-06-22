# Tessera Architecture

## 1. Purpose

Tessera turns messy AI and engineering inputs into validated, reviewable, export-ready artifacts. It is a plugin-based SDK hub. Each domain (evals, RAG, prompts, API tracing, repo mapping, etc.) ships as its own *job pack* on top of a shared runtime.

The promise of every pack is the same:

```text
messy source data
  ↓
normalize to canonical schema
  ↓
validate with quality gates
  ↓
generate reviewable artifacts
  ↓
export to downstream frameworks
```

Core owns the runtime contract. Job packs own domain behavior.

## 2. Core vs job packs

```text
tessera-core
  workspace + run context
  JobPack abstract base class
  plugin loaders (CLI + job packs)
  column detection (confidence-scored, with overrides)
  artifact writers (JSONL, CSV, YAML, Markdown)
  CLI shell (typer)

tessera-evals
  EvalRecord schema (pydantic BaseModel)
  CSV → canonical record compiler
  task-keyed rubric templates
  golden candidate builder
  data quality + coverage reports
  EvalsPack: implements JobPack

tessera-prompts
  PromptCase / PromptVariable / PromptExample schemas (pydantic BaseModel)
  directory walker (file form and folder form)
  frontmatter + body parser
  variable extractor + validator
  catalog and validation reports
  PromptsPack: implements JobPack

tessera-skills
  SkillManifest / SkillFile / SkillDependencies schemas (pydantic BaseModel)
  folder walker (folder form only; matches Anthropic Skills convention)
  frontmatter + body parser + file inventory + classification
  dependency extractor (bash commands, MCP tools, skill-to-skill refs)
  description overlap detector (token Jaccard)
  catalog, validation, coverage, and dependencies reports
  SkillsPack: implements JobPack

tessera-recipes
  Recipe / RecipeStep / RecipeIO schemas (pydantic BaseModel)
  file + folder walker
  frontmatter + body parser
  graph engine (reference parsing, edge inference, cycle detection, topo sort)
  graph validator (cycles, dangling refs, reachability)
  catalog, validation, coverage, machine plan + human execution plan
  RecipesPack: implements JobPack

tessera-api
  ApiRequest / ApiAuth / Redaction schemas (pydantic BaseModel)
  curl parser (shlex tokenizer, flag walker, multi-command splitter)
  secret redactor (header/query/basic-auth/body, masked at parse time)
  hygiene validator (insecure scheme, secret-in-URL, no-auth, duplicates)
  catalog, validation, coverage, redactions audit report
  ApiPack: implements JobPack

tessera-rag
  RagDocument / RagQuery / RagCase schemas (pydantic BaseModel)
  corpus loader (walk corpus/, doc id = relative path without suffix, sha256)
  queries loader (jsonl or yaml)
  reference validator (dangling doc refs, orphan docs, missing targets/answers)
  dataset, corpus index, validation, coverage, retrieval-targets report
  RagPack: implements JobPack

tessera-repo
  RepoFile / RepoManifest / RepoMap schemas (pydantic BaseModel)
  scanner (walk repo, ignore build/vendor dirs, classify language + kind, count loc)
  manifest parsers (pyproject / package.json / requirements / cargo / go.mod)
  hygiene validator (readme/license/tests/ci signals, large files)
  files index, aggregate map JSON, catalog, validation, coverage, dependencies report
  RepoPack: implements JobPack

tessera-changelog
  Commit schema (pydantic BaseModel)
  conventional-commit parser (type/scope/breaking/PR)
  git log reader (read-only subprocess) + commits.jsonl fallback
  hygiene validator (non-conventional, WIP, breaking, empty subject)
  commits index, CHANGELOG.md, release notes, validation, coverage
  ChangelogPack: implements JobPack

tessera-config
  ConfigKey schema (pydantic BaseModel)
  env-file parser + example/real classifier
  code scanner (os.getenv / os.environ / process.env references)
  secret detection + masking (redact at load time)
  drift validator (committed secret, undocumented, missing, unused)
  inventory, catalog, validation, coverage, drift report
  ConfigPack: implements JobPack

tessera-openapi
  Endpoint / SpecInfo schemas (pydantic BaseModel)
  spec loader (OpenAPI 3.x + Swagger 2.0; json/yaml; operation iterator)
  lint validator (path params, operationIds, responses, security, ...)
  endpoint catalog, validation, coverage, tag-grouped surface
  OpenApiPack: implements JobPack

tessera-docs
  DocSymbol schema (pydantic BaseModel)
  ast scanner (modules/classes/functions/methods + docstring presence)
  coverage validator (missing docstrings by kind, low-coverage threshold)
  symbols index, coverage report, undocumented list
  DocsPack: implements JobPack

tessera-sql
  SqlStatement / SqlTable schemas (pydantic BaseModel)
  lightweight parser (strip comments, quote-aware statement split, classify, extract)
  safety validator (delete/update without where, drop without if-exists, no PK, select *)
  statement + table catalogs, validation, coverage
  SqlPack: implements JobPack

tessera-todo
  TodoItem schema (pydantic BaseModel)
  marker scanner (TODO/FIXME/HACK/XXX/BUG/NOTE/OPTIMIZE/REFACTOR/DEPRECATED)
  triage validator (high-priority markers, ownerless TODOs, empty markers)
  prioritized backlog, coverage, owner-grouped report
  TodoPack: implements JobPack

tessera-deps
  Dependency schema (pydantic BaseModel)
  manifest parsers (requirements / pyproject / package.json / cargo / go.mod)
  pinning classifier (pinned / ranged / unpinned per ecosystem)
  audit validator (unpinned, duplicate, conflicting constraints)
  inventory, coverage, duplicates report
  DepsPack: implements JobPack

tessera-tests
  TestCase schema (pydantic BaseModel)
  ast test scanner (functions/methods, decorators, assertion counting)
  hygiene validator (no-assertion, skipped, xfail)
  test inventory, coverage, not-running report
  TestsPack: implements JobPack

tessera-links
  Link schema (pydantic BaseModel)
  markdown link extractor + heading-anchor collector (fence-aware)
  resolver (internal file existence, anchor existence, orphan detection)
  link inventory, coverage, broken-links report
  LinksPack: implements JobPack

tessera-dockerfile
  Instruction schema (pydantic BaseModel)
  Dockerfile parser (line-continuation join, multi-stage FROM ... AS tracking)
  hygiene/security validator (latest tag, root, secret-in-ENV, ADD vs COPY, healthcheck)
  instruction inventory, validation, coverage
  DockerfilePack: implements JobPack

tessera-i18n
  LocaleFile schema (pydantic BaseModel)
  locale loader (json flatten, locale-name inference, reference selection)
  coverage validator (missing/extra/empty keys, low coverage)
  coverage table, per-locale missing-keys report
  I18nPack: implements JobPack

tessera-schema
  SchemaDoc schema (pydantic BaseModel)
  JSON Schema loader (detection, structure extraction)
  structural validator (required-not-in-properties, missing type, open objects)
  schema catalog, validation, coverage
  SchemaPack: implements JobPack

tessera-license
  LicenseFinding schema (pydantic BaseModel)
  license detector (content signatures + manifest license fields) + classifier
  hygiene validator (copyleft, mismatch, missing file, unrecognized)
  license inventory, validation, coverage
  LicensePack: implements JobPack

tessera-app  (CLI-only plugin; orchestrates JobPacks, is not one)
  detect (which packs apply to a project directory)
  orchestrator (run applicable packs via load_jobpacks(), summarize, write manifest)
  markdown (small stdlib Markdown -> HTML renderer)
  dashboard (self-contained index.html from a run output directory)
  registers tessera run / detect / dashboard under tessera.commands only
```

Rule: core never imports from any pack. Packs depend on core. New packs follow the same shape.

## 3. JobPack lifecycle

Every pack implements one abstract base class:

```python
class JobPack(ABC):
    name: str
    version: str

    @abstractmethod
    def normalize(self, input_path, options) -> list[Any]: ...

    @abstractmethod
    def validate(self, records, options) -> list[ValidationFinding]: ...

    @abstractmethod
    def generate(self, records, ctx, options) -> list[Artifact]: ...

    def run(self, input_path, ctx, options) -> list[Artifact]:
        records = self.normalize(input_path, options)
        findings = self.validate(records, options)
        artifacts = self.generate(records, ctx, options)
        ctx.metadata["record_count"] = len(records)
        ctx.metadata["finding_count"] = len(findings)
        ctx.metadata["findings"] = findings
        return artifacts
```

That is the contract. `run()` is concrete on purpose; the three abstract steps are the only things a pack must implement. No middleware, no event bus, no `before_*` / `after_*` hooks. The pack does its job; the runtime stitches it together.

`RunContext` carries `run_id`, `job_name`, `output_dir`, `created_at`, and a `metadata` dict that the runtime populates with run-level summary data after `run()`.

## 4. CLI plugins vs job-pack plugins

There are two entry-point groups, deliberately separated.

```text
tessera.commands  = CLI extension hook
tessera.jobpacks  = workflow execution contract
```

- `tessera.commands` lets a pack add subcommands to the `tessera` CLI. Loaded by `load_cli_plugins(app)`.
- `tessera.jobpacks` registers a factory function that returns a `JobPack` instance. Loaded by `load_jobpacks()`. The loader asserts `isinstance(pack, JobPack)` and rejects anything else.

A pack can register in one group, the other, or both. The evals pack registers in both: CLI commands for ergonomics, and the JobPack for programmatic and inter-pack use. The example pack (in core) registers only as a job pack, to keep one non-evals implementer honest.

This split exists so we can add packs that are pure CLI utilities (no canonical artifacts) without forcing them through the JobPack contract, and add packs that other code consumes programmatically (no CLI surface) without requiring a CLI registration.

## 5. Eval pack v0.2 flow

```text
CSV input
  ↓ load_eval_records()
    detect_column() for input/expected/context (confidence-scored, override-aware)
    detect_by_content() fallback for input when header detection fails
    analyze_column() for each detected column (type, completeness, length, distinct)
    deduplicate by input
    flag empty inputs and missing expected answers
  ↓ validate_eval_records()
    turn detection failures + per-row notes into ValidationFinding objects
  ↓ write_eval_artifacts()
    dataset.jsonl            (EvalRecord, pydantic-serialized)
    golden_candidates.csv    (rows needing human review)
    rubric.yaml              (deterministic, task-keyed template)
    coverage_report.md       (task breakdown + needs-review count)
    data_quality_report.md   (detection table + analysis table + warnings + override hint)
```

The CLI is a thin wrapper: it builds a `RunContext`, calls `pack.run()`, prints the artifact table and run summary. Nothing in the CLI knows how `dataset.jsonl` is laid out.

Column detection uses five confidence tiers:

```text
1.00  manual override
0.95  exact match (raw or normalized: strip common prefixes/suffixes)
0.85  token match (candidate is a token of the header)
0.70  substring match
0.40  content fallback (longest free-text column; input-field only)
0.00  no match
```

Normalization strips leading wrappers (`customer_`, `user_`, `agent_`, `the_`, ...) and trailing wrappers (`_text`, `_field`, `_value`, `_body`, ...) before re-checking against candidates. This lifts headers like `customer_question` and `request_body` from token-match (0.85) to exact-normalized-match (0.95) without expanding the candidate lists.

Content fallback fires only for the input field, and only when header detection yields zero matches. It picks the column with the longest average non-empty text length, capped at 0.40 confidence so the quality report always shows it as low-confidence with an override hint.

Column analysis profiles each detected column for inferred type (`text` / `short` / `category` / `numeric` / `empty`), completeness, average and max length, and distinct value count. The result is rendered as a `## Column Analysis` table in `data_quality_report.md` so reviewers can tell at a glance whether the picked column actually looks like what we expected it to be.

Pack-owned candidate lists live in `tessera_evals/compiler.py`. Future packs (`tessera-rag`, `tessera-prompts`, ...) own their own candidate vocabularies; the detection mechanism in `tessera_core.detect` is generic.

Sample messy CSVs covering the detection paths live under `examples/evals/messy/`: `compound_prefix.csv` (prefix normalization), `wrapper_suffix.csv` (suffix normalization), `unusual_aliases.csv` (broader candidate vocabulary), `cryptic_kb.csv` (token + normalized hits without prior knowledge of headers). All four compile correctly with no manual override.

`data_quality_report.md` is honest about uncertainty: it always shows the detection table with confidence and reason, and emits a recommended-override block whenever any confidence drops below 0.95.

## 5b. Prompts pack v0.1 flow (second JobPack implementer)

```text
prompt directory (or single .prompt.md file)
  ↓ load_prompt_records()
    discover_prompt_files() walks: `<name>.prompt.md` and `<name>/PROMPT.md`
    parse_prompt_file() reads YAML frontmatter and markdown body
    extract `{{var}}` placeholders from body
  ↓ validate_prompt_records()
    per-record:  missing name, non-canonical name, invalid SemVer,
                 missing/short description, empty body,
                 undeclared/unused variables,
                 examples missing required variables
    cross-record: duplicate (name, version) pairs
  ↓ write_prompt_artifacts()
    index.jsonl              canonical PromptCase rows
    examples.jsonl           inline examples in a flat dict shape
    index.md                 human-readable catalog
    validation_report.md     findings grouped by severity
    coverage_report.md       tag distribution + example coverage + languages
```

Why two input shapes: a single `<name>.prompt.md` keeps simple prompts ergonomic; a `<name>/PROMPT.md` folder leaves room for attachments (test cases, variants, large reference files) without changing the schema. The same loader handles both; the parsed `PromptCase.metadata["source_form"]` records which form was used.

Why `examples.jsonl` is a flat-dict shape rather than `EvalRecord`: avoids a pack-to-pack import. When `tessera-evals` later grows a `--from-prompts` ingester, the conversion is one-directional and explicit; the two packs do not share a Python module.

**Contract finding (verified during this branch):** `JobPack.normalize(input_path, options)` accepts both a CSV file path (evals) and a directory path (prompts) without changes to the core ABC. The contract held under a second, structurally different domain. No core changes were needed for v0.1 of the prompts pack.

## 5c. Skills pack v0.1 flow (third JobPack implementer)

```text
skills root directory
  ↓ load_skill_records()
    discover_skill_folders() walks for any folder containing SKILL.md
    parse_skill_folder() reads frontmatter + body, inventories sibling files,
                         classifies each file (skill/script/reference/example/data/other),
                         extracts dependencies from body:
                           - bash commands (first word of each line in bash fences)
                           - MCP tools matching mcp__*
                           - skill-to-skill refs matching /<slug>
  ↓ validate_skill_records()
    per-record:   missing/non-canonical name, missing/short description,
                  description_lacks_triggers, invalid SemVer, empty body
    cross-record: name collisions, description overlap (token Jaccard)
                    - 0.50 ≤ sim < 0.70 → warning
                    - 0.70 ≤ sim       → error (likely silent misfire)
  ↓ write_skill_artifacts()
    index.jsonl              canonical SkillManifest rows
    index.md                 human catalog (name, version, tags, files, size, deps)
    validation_report.md     findings grouped by severity
    coverage_report.md       tag distribution + file-kind coverage
    dependencies_report.md   aggregate bash/MCP/skill surface + overlap matrix
```

Why folder-only (no single-file form): Anthropic Skills are canonically folders. A skill expects supporting files alongside (scripts, references, examples), and the file inventory is a real part of the manifest. Allowing a single-file form would require a parallel schema. The single-file ergonomic that prompts needs is not a skills requirement; aligning tightly with the upstream convention is the future-proof choice.

Why a separate `dependencies_report.md`: skills make implicit runtime claims (this skill needs `git`, needs an `mcp__*` tool, calls another skill). Surfacing these in one place makes a skill collection auditable before deployment. This is the skills-specific report that prompts and evals do not have.

Why a description-overlap detector: skills are matched by an LLM against the user's intent. When two skills have similar descriptions, the wrong one fires. The overlap matrix in `dependencies_report.md` makes that risk visible at compile time.

**Contract finding (verified during this branch):** `JobPack` needed no changes for the third domain either. The same `normalize → validate → generate → run` lifecycle handles a folder-of-folders input with attachments and per-record file inventories. Three real implementers from genuinely different domains (CSV rows, prompt files, skill folders) now ride the same contract unchanged. This is the strongest signal yet that the v0.1 contract is right.

## 5d. Recipes pack v0.1 flow (fourth JobPack implementer, the contract's hardest test)

Recipes are the richest record type in Tessera: a recipe is a workflow of steps where steps reference each other and inputs flow between them. This is a graph, not a flat record, and it is the case most likely to force a contract change. It did not.

```text
recipe directory (or single .recipe.md file)
  ↓ load_recipe_records()
    discover_recipe_files() walks `<name>.recipe.md` and `<name>/RECIPE.md`
    parse_recipe_file() reads frontmatter (inputs, outputs, steps) + body
  ↓ validate_recipe_records()
    frontmatter: name / version / description / no_steps
    per-step:    missing/duplicate step id, self-dependency,
                 dangling needs, dangling ${steps.X} / ${inputs.X} references
    graph:       cycle detection (reports the cycle path)
    semantics:   unproduced declared outputs, unreachable steps
  ↓ write_recipe_artifacts()
    index.jsonl              canonical Recipe rows
    plans.jsonl              machine plan: topo order + edges + cycle per recipe
    index.md                 catalog with acyclic flag
    validation_report.md     findings grouped by severity
    coverage_report.md       step counts, acyclic ratio, tags
    execution_plans.md       per-recipe topological order + dependency edges
```

The graph engine (`tessera_recipes/graph.py`) is the pack's distinctive piece:

- **Edge inference.** A step's dependencies are the union of its explicit `needs` and the steps referenced as `${steps.X.output}` in its `inputs`. Authors can wire steps either way; the engine reconciles both.
- **Cycle detection + topological sort.** Kahn's algorithm produces a deterministic execution order (ties broken alphabetically for reproducible artifacts). On a cycle, a DFS returns one representative cycle path for the error message.
- **Reference integrity.** `${inputs.X}` must name a declared recipe input; `${steps.X}` must name a real step. Both are validated, not just parsed.

Why this matters for the contract: the graph lives entirely inside the pack's `validate` and `generate` steps. The DAG, the topo sort, the cycle reporting — none of it leaked into `tessera-core`. Core still sees a list of records and a list of findings. The richest possible record type was absorbed by the existing lifecycle without a single new core concept.

**Contract conclusion (after four packs):** Four implementers now ride the v0.1 `JobPack` contract unchanged — flat CSV rows (evals), single-file or directory prompt files (prompts), folder-of-folders with attachments (skills), and a dependency graph of steps (recipes). The contract has survived flat records, file collections, and a true graph. The v0.1 `JobPack` ABC is empirically locked; there is no pending need for a v2. Future packs should be built against it as-is, and any proposal to change it should be treated as a breaking change requiring the same bar these four packs cleared.

## 5e. Inter-pack composition (data contract, not code contract)

Packs compose through **artifacts**, not imports. The first composition shipped is `tessera evals compile --from-prompts`: the evals pack ingests a prompts-pack `examples.jsonl` and produces a normal eval pack.

```text
prompt files
  ↓ tessera prompts compile
examples.jsonl   (flat-dict interchange format)
  ↓ tessera evals compile --from-prompts
dataset.jsonl    (canonical EvalRecord rows, with origin/prompt_name provenance)
```

The load-bearing decision (made when the prompts pack shipped) was to emit `examples.jsonl` as a **flat dict shape, not as serialized `EvalRecord` objects**. That choice pays off here: `tessera_evals` reads the documented `examples.jsonl` shape (`id`, `rendered_prompt`, `input_variables`, `expected`, `prompt_name`, ...) without importing `tessera_prompts`. The two packs share a *data contract*, not a *code dependency*. Either can be installed without the other; the interchange format is the seam.

Inside evals, the prompts source is just another `normalize` path. `load_eval_records` dispatches on `options["source"] == "prompts"` to `from_prompts.load_prompt_examples`, which maps prompt-example rows to `EvalRecord`s (input from `rendered_prompt`, expected from `expected`) and stamps `metadata.origin = "prompts"`. The validate and write steps are unchanged; column-detection findings are skipped because the field mapping is fixed, and the quality report shows a "Field Mapping (prompts source)" section instead of a detection table. No new core concepts; the composition rides the same `JobPack` lifecycle.

This is the template for future inter-pack flows (e.g. recipes referencing skills, or evals ingesting an api-trace pack): one pack emits a documented flat interchange artifact, the consuming pack adds a `source` path that reads it. Packs never import each other.

## 5f. API pack v0.1 flow (curl ingestion, redaction-first)

The api pack turns messy curl/HTTP traces into a canonical API surface map. Its defining concern is **secret safety**: no plaintext secret may reach any artifact.

```text
.curl / .sh files
  ↓ load_api_records()
    discover_curl_files() walks *.curl and *.sh
    split_curl_commands() joins line-continuations, splits on each `curl` token
    parse_curl() tokenizes (shlex), walks flags (-X, -H, -u, -d, --url, ...),
                 and REDACTS every secret inline before building the record
  ↓ validate_api_records()
    per-request: insecure_scheme, missing_host, secret_in_url_query, no_auth_detected
    cross-request: duplicate_request, multiple_hosts
  ↓ write_artifacts()
    index.jsonl              canonical, redacted ApiRequest rows
    index.md                 catalog (method, host, path, auth kind, redaction count)
    validation_report.md     hygiene findings
    coverage_report.md       method / host / auth-kind distribution
    redactions_report.md     audit trail of every secret masked
```

Redaction-first design (the load-bearing safety property):

- **Redaction happens at parse time**, inside `parse_curl`, before any value is placed into an `ApiRequest`. The canonical record is constructed already-clean; there is no window where a record holds a raw secret.
- **The raw command is never stored.** An early implementation kept a `raw_command_preview` in metadata for debugging; the no-leak test caught that it re-introduced the very secrets being stripped. It was removed and replaced with a synthesized `summary` (`METHOD host/path`). The lesson is encoded as a permanent test.
- **`mask()` reveals at most a couple of leading characters and the length, never the tail.** Previews like `sk…(redacted, len=48)` are enough to recognize a value without reconstructing it.
- **Every redaction is audited.** Header, query, basic-auth, and body-field redactions all append a `Redaction` with location, kind, and masked preview, surfaced in `redactions_report.md`.
- **A dedicated test asserts no raw secret string appears in any output file.** This is the pack's headline guarantee, enforced mechanically rather than by inspection.

Live request execution (the API caller, batch runner, streaming response capture) is intentionally **out of scope for v0.1**, the same way LLM rubric enrichment is deferred in evals. v0.1 is the offline, side-effect-free pass. When execution lands, it will be a separate opt-in path with its own network and secret-handling considerations; the offline canonicalization here is the foundation it will build on.

Contract note: the api pack rides the same `JobPack` lifecycle as the other five. Parsing, redaction, and validation all live inside `normalize`/`validate`; nothing about secrets or curl reached `tessera-core`.

## 5g. RAG pack v0.1 flow (corpus + queries -> retrieval eval dataset)

The rag pack builds a canonical retrieval eval dataset from a document corpus and a set of queries, verifying that every query's gold document references actually exist.

```text
input directory (corpus/ + queries.jsonl|.yaml)
  ↓ load_rag_records()
    load_corpus() walks corpus/, each doc id = corpus-relative path w/o suffix,
                  captures title (first H1), char/word counts, sha256
    parse queries (jsonl or yaml) into RagQuery, then RagCase
                  (query + expected_answer + relevant_doc_ids + review_status)
  ↓ validate_rag_records()
    corpus:  empty_corpus, empty_document, duplicate_doc_id
    queries: missing_query_text, duplicate_query
    refs:    dangling_doc_reference (query points at a doc not in corpus),
             query_without_relevant_docs (no retrieval target),
             query_without_expected_answer (needs human review)
    corpus reachability: orphan_document (no query references it)
  ↓ write_artifacts()
    dataset.jsonl            canonical RagCase rows
    corpus_index.jsonl       RagDocument rows (id, title, counts, sha256)
    validation_report.md     findings grouped by severity
    coverage_report.md       answer/target coverage, orphan count, avg targets
    retrieval_targets.md     per-query gold document set with titles
```

Like the api pack (no HTTP execution) and evals (no LLM calls), the rag pack does **no retrieval**: no embeddings, no vector store, no scoring. v0.1 produces the validated, internally-consistent dataset a retriever would later be scored against. The defining property here is referential integrity — `dangling_doc_reference` catches a query whose gold target does not exist in the corpus, which would otherwise silently corrupt any retrieval metric computed downstream. The `sha256` per document gives a stable content fingerprint for future corpus-versioning and change detection.

Contract note: the rag pack is the seventh implementer (counting the in-core example pack) and rides the unchanged `JobPack` lifecycle. The corpus walk, the dual jsonl/yaml query loader, and the cross-reference validation all live inside `normalize`/`validate`; core was not touched.

## 5h. Repo pack v0.1 flow (repository -> structural map)

The repo pack turns a repository into a validated structural artifact: a per-file inventory, an aggregate map (languages, layout, manifests, signals), the declared dependency surface, and repo-hygiene findings. It reads code but never runs it and makes no network calls.

```text
repository directory
  ↓ load_repo_records()
    scan_repo() walks the tree, skipping IGNORE_DIRS (.git, .venv, node_modules,
                dist, build, target, __pycache__, ...); for each file records
                language (by extension), kind (source/test/config/docs/build/
                data/asset/other), lines of code, and byte size
    detect_and_parse() best-effort parses dependency manifests (pyproject,
                package.json, requirements.txt, Cargo.toml, go.mod)
    build_map() aggregates languages, top-level layout, manifests, and hygiene
                signals (has_readme/license/tests/ci/gitignore)
  ↓ validate_repo_records()
    empty_repo, missing_readme, missing_license, no_tests_detected,
    no_dependency_manifest, no_ci_config, large_source_file
  ↓ write_artifacts()
    files.jsonl              one RepoFile per file
    repo_map.json            aggregate RepoMap
    index.md                 human map (signals, languages, layout, manifests)
    validation_report.md     hygiene findings
    coverage_report.md       files by kind + test-to-source ratio
    dependencies_report.md   declared dependencies across all manifests
```

Two design notes carried over from the rest of the suite:

- **No execution, ever.** The pack reads file contents for line counts and manifest parsing, but never imports or runs the target repo, and makes no network calls. Same discipline as api (no HTTP), evals (no LLM), and rag (no retrieval).
- **Manifest parsing is best-effort and dependency-light.** It uses stdlib `tomllib` when available (Python 3.11+) and a regex fallback on 3.10, and a manifest that cannot be parsed yields an empty dependency list rather than a hard error. Declared dependencies are informational surface, not a contract to enforce.

Contract note: eighth implementer, unchanged `JobPack` lifecycle. The walk, classification, manifest parsing, and signal computation all live in `normalize`; the hygiene rules live in `validate`. Core was not touched. Eight packs across flat rows, files, folders, a graph, a corpus, and now a whole repository tree all ride the same v0.1 contract.

## 5i. The app: orchestration layer and the payoff of two plugin groups

`tessera-app` is the unifying surface over the hub. It is deliberately **not** a JobPack: it registers only under `tessera.commands`, and it consumes JobPacks through `load_jobpacks()`. This is the first real use of the two-group split introduced in section 4 — until now every pack registered in both groups, so the distinction was latent. The app validates it: a pure-CLI extension that orchestrates the workflow packs without implementing the workflow contract.

```text
tessera run --input <project>
  ↓ detect_packs()
    inspect the project tree (ignoring build/vendor dirs) and decide which packs
    apply: prompt files -> prompts, SKILL.md -> skills, .recipe.md -> recipes,
    curl files -> api, corpus/ + queries -> rag, a CSV -> evals (task generic),
    source/manifest -> repo
  ↓ run_project()
    load_jobpacks(); for each detection, run pack.run(input, ctx, options) into
    output/<pack>/; never raise on a single pack's failure (record and continue);
    write run_manifest.json summarizing record/finding/error counts + artifacts
  ↓ build_dashboard()
    render output/index.html: headline cards + per-pack sections, each pack's
    Markdown reports converted to HTML by a small stdlib renderer
```

Design properties:

- **Fault isolation.** `run_project` wraps each pack in try/except. One pack erroring (a malformed CSV, an empty corpus) is reported in the run table and the dashboard, but the other packs still run and the dashboard still builds. The orchestrator's job is to never let one bad input sink the whole run.
- **Self-contained output.** The dashboard is a single HTML file with inline CSS and no JavaScript or external assets. It can be committed to a repo, emailed, or served as a static file. A test asserts the absence of any `http(s)://` reference and any `<script>` tag.
- **No new dependencies.** The Markdown-to-HTML renderer is ~80 lines of stdlib (`re` + `html`), tuned to the exact subset the pack reports use (ATX headings, pipe tables, bullet lists, fenced code, bold, inline code). The hub gains a dashboard without taking on a Markdown library.
- **Re-derivable.** `tessera dashboard --input <run>` rebuilds the HTML from the run directory alone (it reads `run_manifest.json` plus each pack's artifacts), so the view is never the source of truth — the artifacts are.

This is where "SDKs as leverage" becomes legible end to end: one command turns a messy project directory into a browsable report spanning evals, prompts, skills, recipes, api, rag, and repo, with each pack still independently usable on its own.

## 5j. Changelog pack v0.1 (git history -> structured changelog)

The changelog pack turns commit history into a grouped `CHANGELOG.md` and release notes. It has two input sources behind one `normalize`: a git repository (read via a read-only `git log --no-merges` subprocess) or a portable `commits.jsonl`. The git path is the only place in the whole hub that shells out, and it does so read-only against version-control metadata: no project code runs, no network is touched, consistent with the no-execution discipline everywhere else.

```text
git repo or commits.jsonl
  ↓ load_changelog_records()
    git source: `git log` with \x1f/\x1e field/record separators (collision-safe)
    jsonl source: parse each line
    parse_subject(): Conventional Commits -> type / scope / breaking / PR number
  ↓ validate_changelog_records()
    source_error, no_commits, empty_subject, non_conventional_commit (info),
    wip_commit, breaking_change
  ↓ write_artifacts()
    commits.jsonl            canonical Commit rows
    CHANGELOG.md             grouped by type, Breaking Changes section first
    release_notes.md         prose summary with highlights
    validation_report.md     commit-hygiene findings
    coverage_report.md       type distribution, % conventional, authors
```

The portable `commits.jsonl` input is deliberate: it keeps the pack testable without a git fixture, and it mirrors the inter-pack interchange pattern — a future pack could emit commit records that this one consumes. The `\x1f`/`\x1e` separators in the git format string avoid the classic bug where a commit subject containing the delimiter corrupts parsing.

Contract note: ninth JobPack implementer, unchanged lifecycle. The git subprocess and the conventional-commit parser live in `normalize`; the hygiene rules in `validate`. Core untouched.

## 5k. Config pack v0.1 (config hygiene + leak check)

The config pack inventories a project's configuration and reports the gaps between what is documented, what is set, and what is actually used. It is the second redaction-first pack (after api): secret values are masked at load time, before any record exists.

```text
project directory
  ↓ load_config_records()
    find_env_files(): classify .env* files into real vs example (example/sample/template)
    parse_env(): KEY=VALUE (export prefix, quotes, inline comments)
    find_code_references(): os.getenv / os.environ / getenv / process.env across source
    aggregate per key: in_env / in_example / in_code; mask secret-named values
  ↓ validate_config_records()
    possible_committed_secret (a secret-named key with a value in a real .env),
    missing_in_example (used in code, undocumented),
    undocumented_env_key (set in .env, undocumented),
    unused_documented_key (documented, never used or set)
  ↓ write_artifacts()
    config_inventory.jsonl, index.md, validation_report.md, coverage_report.md,
    drift_report.md (used-but-undocumented / set-but-undocumented / documented-but-unused)
```

The three-way set difference (declared in an example, set in a real env, referenced in code) is the heart of the pack: each pairwise gap is a distinct, actionable drift finding. The leak check is deliberately conservative and name-based in v0.1 (same approach as the api pack), and like api it carries a test asserting no raw secret value reaches any artifact.

Contract note: tenth JobPack implementer; core untouched. The masking utility is kept local to the pack rather than imported from api — packs never depend on each other; a shared masking primitive in core is a possible future refactor, not a v0.1 coupling.

## 5l. OpenAPI pack v0.1 (spec lint -> endpoint catalog)

The openapi pack parses an OpenAPI 3.x or Swagger 2.0 document into a canonical endpoint catalog and lints it for common spec-hygiene problems. It pairs with the api pack: api characterizes traffic that exists, openapi characterizes the contract that describes it.

```text
spec file (.json / .yaml)
  ↓ load_openapi_records()
    find_spec_file(): openapi.* / swagger.* or any yaml/json mentioning openapi/swagger
    load_spec(): json or yaml
    iter_operations(): paths -> {method: operation}, merging path-level parameters
    build Endpoint: method/path/operationId/tags/path-params/declared-params/
                    responses/deprecated/secured
  ↓ validate_openapi_records()
    invalid_spec, no_endpoints, duplicate_operation_id, missing_operation_id,
    path_param_not_declared, declared_param_not_in_path, missing_2xx_response,
    missing_summary, no_tags, no_security, deprecated_endpoint
  ↓ write_artifacts()
    endpoints.jsonl, index.md, validation_report.md, coverage_report.md,
    surface.md (the API surface grouped by tag)
```

The load-bearing lint is `path_param_not_declared`: a `{param}` in a path template with no matching `parameters` entry is a real bug that breaks generated clients and docs. The pack handles both spec dialects — OpenAPI 3.x `requestBody`/`servers` and Swagger 2.0 `in: body` params/`host` — behind one `Endpoint` shape, so downstream consumers do not care which dialect produced the catalog.

Contract note: eleventh JobPack implementer; core untouched. Spec parsing lives in `normalize`, lint rules in `validate`. Eleven packs now span tabular rows, document files, folders, graphs, corpora, repo trees, curl traces, env config, git history, and API specs — all on the same v0.1 contract.

## 5m. Docs pack v0.1 (Python docstring coverage)

The docs pack measures docstring coverage for a Python codebase. It parses each file with the standard-library `ast` module and never imports or executes the code — important, since the target may have side effects or uninstalled dependencies.

```text
project directory
  ↓ load_docs_records()
    discover_py_files(): walk .py, skip build/vendor dirs and (by default) tests
    extract_symbols(): ast.parse each file; record the module symbol plus every
                       class/function/method with ast.get_docstring presence;
                       public = name does not start with "_"
  ↓ validate_docs_records()
    missing_module/class/function/method_docstring, low_doc_coverage (< 80%),
    parse_error, no_public_symbols
  ↓ write_artifacts()
    symbols.jsonl, index.md, validation_report.md,
    coverage_report.md (by kind + lowest-coverage files),
    undocumented.md (every undocumented public symbol with file:line)
```

`undocumented.md` is the actionable artifact: a file:line list a developer can work straight down. Privates and dunders are excluded from the public-coverage denominator, matching the convention of tools like interrogate, so the number reflects the API surface that actually needs docs.

Contract note: twelfth JobPack implementer; core untouched. `ast` parsing in `normalize`, coverage rules in `validate`. Twelve JobPacks (plus the in-core example) and the app now ride the v0.1 contract without a single change to `tessera-core` since it was written.

## 5n. SQL pack v0.1 (migration safety lint)

The sql pack parses `.sql` files and flags the migration mistakes that cause incidents. It does not connect to a database or execute anything; parsing is deliberately lightweight (comment stripping, quote-aware statement splitting, keyword/regex classification).

```text
.sql files
  ↓ load_sql_records()
    split_statements(): strip -- and /* */ comments, split on top-level ; (quote-aware)
    classify(): kind (create_table/index, alter, drop, insert, update, delete, select) + target
    statement_flags(): has_where, if_exists, select_star
    parse_create_table(): column names + PRIMARY KEY presence
  ↓ validate_sql_records()
    delete_without_where (error), update_without_where, drop_without_if_exists,
    table_without_primary_key, select_star
  ↓ write_artifacts()
    statements.jsonl, tables.jsonl, index.md, validation_report.md,
    coverage_report.md, tables.md
```

The load-bearing finding is `delete_without_where` at error severity: an unscoped `DELETE`/`UPDATE` is one of the most common destructive-migration mistakes, and the quote-aware splitter exists specifically so a semicolon inside a string literal does not fool the statement boundary detection. v0.1 is honest about being heuristic rather than a full dialect parser — it targets migration and schema files, which are the high-value review surface.

Contract note: thirteenth JobPack implementer; core untouched. Parsing and table extraction in `normalize`, safety rules in `validate`.

## 5o. Todo pack v0.1 (marker backlog)

The todo pack scans source for code markers and turns them into a triaged, owner-grouped backlog. It is the lightest pack in the hub and the most universally applicable: almost any codebase has `TODO`/`FIXME` markers, and they are rarely tracked anywhere.

```text
project directory
  ↓ load_todo_records()
    scan_todos(): line-by-line regex over source/doc files for
    TODO/FIXME/HACK/XXX/BUG/NOTE/OPTIMIZE/REFACTOR/DEPRECATED, capturing the
    optional (owner) and trailing description; assign priority (high/normal/low)
  ↓ validate_todo_records()
    high_priority_marker (FIXME/HACK/XXX/BUG), todo_without_owner, marker_without_text
  ↓ write_artifacts()
    todos.jsonl, index.md (high priority first), validation_report.md,
    coverage_report.md (by priority/marker/file), by_owner.md
```

Priority is assigned by marker class so the backlog sorts itself: `FIXME`/`HACK`/`XXX`/`BUG` are high, `TODO`/`REFACTOR` normal, `NOTE`/`OPTIMIZE`/`DEPRECATED` low. The `by_owner.md` artifact turns `TODO(owner):` annotations into per-person worklists. Detection is intentionally permissive (it matches the marker anywhere on a line, not only inside a parsed comment) which trades a few false positives for being fully language-agnostic.

Contract note: fourteenth JobPack implementer; core untouched. Fourteen JobPacks plus the in-core example and the app, all on the unchanged v0.1 contract.

## 5p. Deps pack v0.1 (dependency pinning audit)

The deps pack audits dependency manifests for supply-chain hygiene. It is a deliberate complement to the repo pack: repo reports *that* a manifest declares dependencies; deps analyses *how* — how tightly each is pinned, and whether the same dependency is declared inconsistently across manifests.

```text
project directory
  ↓ load_deps_records()
    walk for requirements*.txt / pyproject.toml / package.json / Cargo.toml / go.mod
    parse each into Dependency(name, ecosystem, scope, constraint, pinning)
    pinning classified per ecosystem: pinned (exact) / ranged (bounded) / unpinned
  ↓ validate_deps_records()
    unpinned_dependency, duplicate_dependency (same name across manifests),
    conflicting_constraint (same name, different constraints across manifests)
  ↓ write_artifacts()
    dependencies.jsonl, index.md, validation_report.md, coverage_report.md,
    duplicates.md
```

`conflicting_constraint` is the highest-value finding: a dependency pinned to `==2.31.0` in one file and `>=2.0` in another is the kind of drift that produces "works on my machine" bugs. Pinning classification is ecosystem-aware (npm `^1.2.3` is ranged, `1.2.3` is exact; cargo bare versions are caret-ranged; go `require` lines are exact), so the coverage numbers mean the same thing across a polyglot repo. Like the repo and config packs, manifest parsing is best-effort and never resolves a lockfile or hits the network.

Contract note: fifteenth JobPack implementer; core untouched.

## 5q. Tests pack v0.1 (test-suite hygiene)

The tests pack audits a Python test suite for the tests that look like coverage but protect nothing: tests with no assertions, and tests that are skipped or expected to fail. It parses with `ast` (no import, no execution), which matters because importing a test module can have side effects or require the project's full dependency tree.

```text
project directory
  ↓ load_test_records()
    discover_test_files(): test_*.py / *_test.py / files under tests/
    extract_tests(): top-level test* functions and test* methods of Test* classes;
                     render decorators to detect skip/xfail/parametrize; count
                     assertions (assert statements, self.assert* calls,
                     pytest.raises/warns blocks)
  ↓ validate_test_records()
    no_assertion_test (warning; excludes skipped/xfail), skipped_test, xfail_test
  ↓ write_artifacts()
    tests.jsonl, index.md, validation_report.md, coverage_report.md,
    not_running.md (skipped + xfail tests)
```

The headline finding is `no_assertion_test`: a `test_*` function with zero detected assertions passes unconditionally and gives false confidence. Assertion detection is deliberately broad (bare `assert`, unittest `self.assert*`, and `pytest.raises`/`warns` context managers) to avoid false positives across testing styles. `not_running.md` answers a question every team eventually asks: which tests are currently turned off?

One self-referential detail: the pack's own `TestCase` pydantic model sets `__test__ = False` so pytest does not try to collect the domain model as a test class — a small but real interaction between a pack that analyzes tests and the test runner it lives under.

Contract note: sixteenth JobPack implementer; core untouched.

## 5r. Links pack v0.1 (markdown link integrity)

The links pack resolves every inline Markdown link and flags the ones that point nowhere: missing target files, dead heading anchors, and docs nothing links to. External URLs are inventoried but never fetched, keeping the check offline and deterministic.

```text
project / docs directory
  ↓ load_link_records()
    discover_md_files(); extract_links() (fence-aware inline [text](href));
    classify external / mailto / anchor / internal;
    internal: resolve target relative to the source file, check existence;
    anchor: GitHub-style slugify headings of the target file and check membership;
    track which md files are referenced -> orphan detection
  ↓ validate_link_records()
    broken_link, broken_anchor, orphan_doc
  ↓ write_artifacts()
    links.jsonl, index.md, validation_report.md, coverage_report.md, broken.md
```

The deliberate non-goal is external link checking: fetching URLs would make the pack slow, flaky, and network-dependent, violating the hub's no-network discipline. Internal integrity — the links most likely to silently rot during refactors — is fully checkable offline, and that is where the value is. Anchor resolution reuses the same slug algorithm GitHub applies to headings, so `foo.md#my-section` is verified against the actual headings of `foo.md`.

Contract note: seventeenth JobPack implementer; core untouched. Seventeen JobPacks (plus the in-core example) and the app, all still on the v0.1 contract.

## 5s. Dockerfile pack v0.1 (image hygiene + security lint)

The dockerfile pack parses Dockerfiles and flags the hygiene and security mistakes that ship insecure or non-reproducible images. It is multi-stage aware and never builds an image.

```text
Dockerfile(s)
  ↓ load_dockerfile_records()
    discover Dockerfile / Dockerfile.* / *.dockerfile; join line continuations;
    parse each instruction; track FROM ... AS <stage> to know stage names
  ↓ validate_dockerfile_records()  (per file)
    unpinned_base_image, latest_tag, runs_as_root (no USER), secret_in_image
    (ENV/ARG secret-named value), add_instead_of_copy, missing_healthcheck
  ↓ write_artifacts()
    instructions.jsonl, index.md, validation_report.md, coverage_report.md
```

Multi-stage awareness is the detail that keeps the lint honest: `FROM base AS final` references an earlier `FROM python:3.12-slim AS base`, so it must not be flagged as an unpinned base image. The pack collects stage names on a first pass, then suppresses `unpinned_base_image`/`latest_tag` for `FROM <stage>` lines. The `secret_in_image` rule is the highest-value security finding: a secret baked into an `ENV`/`ARG` persists in the image's layer history even if later removed.

Contract note: eighteenth JobPack implementer; core untouched.

## 5t. i18n pack v0.1 (translation coverage)

The i18n pack compares locale files against a reference and reports translation gaps. It flattens nested JSON keys so it works with both flat and structured locale formats.

```text
locale directory
  ↓ load_i18n_records()
    discover *.json (skipping package.json/tsconfig/...); infer locale from filename;
    flatten nested keys to dot notation; pick reference (en, else most-keys);
    per locale compute missing / extra / empty keys + coverage vs reference
  ↓ validate_i18n_records()
    missing_translations, extra_keys, empty_values, low_coverage (<90%),
    single_locale, parse_error
  ↓ write_artifacts()
    locales.jsonl, index.md (coverage table), validation_report.md,
    coverage_report.md, missing_keys.md (the actionable per-locale list)
```

Two design choices make it practical: keys are flattened (`menu.file.open`) so a missing leaf in a nested structure is caught, not just a missing top-level block; and the reference is auto-selected (`en` if present, else the most complete locale) so the pack needs no configuration to produce a useful first report. `missing_keys.md` is the artifact a translator works straight down.

Contract note: nineteenth JobPack implementer; core untouched.

## 5u. Schema pack v0.1 (JSON Schema lint)

The schema pack catalogs JSON Schema documents and flags structural problems. It reads the schemas themselves (not instance data) and needs no network.

```text
schema files
  ↓ load_schema_records()
    discover *.json (skipping package.json/tsconfig/...); treat as a schema when
    it has $schema / properties / $defs / a schema-style root type;
    extract id, dialect, title, type, properties, required, $defs
  ↓ validate_schema_records()
    required_not_in_properties (error), missing_type, object_without_properties,
    additional_properties_unset, missing_schema_version, missing_title
  ↓ write_artifacts()
    schemas.jsonl, index.md, validation_report.md, coverage_report.md
```

The load-bearing finding is `required_not_in_properties`: a `required` entry with no matching `properties` declaration is a schema that can never validate as intended, and it is easy to introduce during refactors. `additional_properties_unset` surfaces the open-by-default behavior that silently lets unexpected fields through — a common source of data-quality drift.

Contract note: twentieth JobPack implementer; core untouched.

## 5v. License pack v0.1 (license hygiene, offline)

The license pack identifies a project's license and classifies it, entirely offline. It deliberately does not do per-dependency license resolution (which needs a network registry); it inspects what the repository itself declares — LICENSE files and manifest `license` fields.

```text
project directory
  ↓ load_license_records()
    read LICENSE / LICENCE / COPYING (identify by content signature);
    read license fields from pyproject / package.json / Cargo.toml;
    normalize to an SPDX-ish id; classify (permissive / weak-copyleft /
    copyleft / public-domain / unknown)
  ↓ validate_license_records()
    no_license, missing_license_file, copyleft_license, license_mismatch,
    unrecognized_license
  ↓ write_artifacts()
    licenses.jsonl, index.md, validation_report.md, coverage_report.md
```

Two findings carry the value: `copyleft_license` surfaces GPL/AGPL obligations a team must review before distribution, and `license_mismatch` catches the common drift where the LICENSE file and the manifest disagree (e.g. a relicensing that updated one but not the other). Detection is signature-based over the license text, so it recognizes the common licenses without any network lookup or embedded full-text corpus.

Contract note: twenty-first JobPack implementer; core untouched. Twenty-one JobPacks plus the in-core example and the app, all still on the unchanged v0.1 contract — the moat is the breadth of domains over one stable interface.

## 6. Schema and type policy

Two layers, on purpose. This is the rule new packs follow.

| Layer | Type system | Why |
|---|---|---|
| Core runtime types (RunContext, Artifact, ValidationFinding) | `@dataclass` | Never cross a wire. Pure runtime carriers. Keeps core dep-light. |
| Pack artifact schemas (EvalRecord, future RAGDocument, PromptCase, ApiTrace) | `pydantic.BaseModel` | These get serialized to disk, read back by other packs, and eventually publish JSON Schema. |
| Pack-specific options | `dict[str, Any]` at first; upgrade to per-pack `pydantic.BaseModel` once a second consumer exists. | Don't pre-build typed options. |

Rationale: pack artifact schemas *are* the boundary. Pydantic gives typed parsing, JSON Schema generation, and a serialization API (`model_dump`, `model_validate`) that the rest of the modern Python AI ecosystem already speaks. Internal runtime carriers don't need any of that, so core stays stdlib-only.

## 7. What is intentionally outside core

These are explicit non-goals for `tessera-core` and `tessera-evals` v0.1. They belong in future packs, not in core.

```text
HTTP / API clients              →  belongs in tessera-api
curl command parsing            →  belongs in tessera-api
batch API execution             →  belongs in tessera-api
streaming response extraction   →  belongs in tessera-api
retrieval / chunking            →  belongs in tessera-rag
prompt eval harness             →  belongs in tessera-prompts
LLM-based rubric enrichment     →  defer; v0.1 uses deterministic templates only
framework adapters              →  defer; export to DeepEval / OpenAI Evals /
                                    RAGAS / LangSmith ships after the canonical
                                    pack is stable
```

Keep core boring and strict. The value is in reliable artifact creation, not framework cleverness.
