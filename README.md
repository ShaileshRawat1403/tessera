# Tessera

Reusable SDK tools that turn messy AI and engineering workflows into validated, reviewable, export-ready artifacts.

Tessera is a plugin-based SDK hub. Each domain ships as its own *job pack* on top of a shared runtime. Every pack follows the same contract:

```text
messy source data → normalize → validate → generate artifacts → export
```

See [`docs/architecture.md`](docs/architecture.md) for the full design.

## Packages

| Package | Role |
|---|---|
| `tessera-core` | Runtime, JobPack contract, plugin loaders, column detection, artifact writers, CLI shell. |
| `tessera-evals` | Compile messy CSV data into a canonical eval pack. |
| `tessera-prompts` | Compile a directory of prompt files (frontmatter + body) into a validated catalog. |
| `tessera-skills` | Validate and catalog Anthropic-style `SKILL.md` skill collections (with file inventory, dep extraction, and description overlap detection). |
| `tessera-recipes` | Compile multi-step workflow recipes into validated, dependency-ordered execution plans (DAG validation: cycles, dangling refs, topological order). |
| `tessera-api` | Parse curl/HTTP traces into a validated, secret-redacted API surface map (redaction at parse time, no request execution). |
| `tessera-rag` | Compile a corpus + queries into a validated retrieval eval dataset (verified doc references, gold retrieval targets; no retrieval execution). |
| `tessera-repo` | Map a repository into a validated structural artifact (file inventory, language/layout map, dependency surface, hygiene signals; no code execution). |
| `tessera-changelog` | Turn git history (or a `commits.jsonl`) into a structured `CHANGELOG.md` + release notes via Conventional Commits parsing. |
| `tessera-config` | Inventory config keys across env files and code, redact leaked secrets, and report config drift (used-but-undocumented, etc.). |
| `tessera-openapi` | Lint an OpenAPI/Swagger spec into a validated endpoint catalog (undeclared path params, duplicate operationIds, missing responses, ...). |
| `tessera-docs` | Measure Python docstring coverage for public symbols (via `ast`; lists undocumented modules/classes/functions/methods). |
| `tessera-sql` | Lint SQL files/migrations into a statement + table catalog (DELETE/UPDATE without WHERE, DROP without IF EXISTS, tables without a primary key, SELECT *). |
| `tessera-todo` | Scan source for TODO/FIXME/HACK/XXX/BUG markers into a triaged, owner-grouped backlog. |
| `tessera-deps` | Audit dependency manifests for pinning discipline, duplicates, and conflicting constraints across ecosystems. |
| `tessera-tests` | Audit a Python test suite via `ast` for hygiene (no-assertion tests, skipped/xfail tests that protect nothing). |
| `tessera-links` | Check Markdown links for broken file references, dead heading anchors, and orphaned docs (external URLs inventoried, not fetched). |
| `tessera-app` | The unifying app: detect which packs apply to a project, run them, and build one self-contained HTML dashboard. CLI-only plugin (orchestrates JobPacks, is not one). |

Future packs follow the same JobPack contract; they do not require changes to core.

> **Naming:** the PyPI distribution names are prefixed `tesserakit-` (e.g. `pip install tesserakit-core`) because `tessera-core` was already taken on PyPI. The import names and CLI are unaffected: you still `import tessera_core` and run `tessera`. So `tesserakit-evals` installs the `tessera_evals` package and contributes to the `tessera` CLI.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip

pip install -e packages/tessera-core \
            -e packages/tessera-evals \
            -e packages/tessera-prompts \
            -e packages/tessera-skills \
            -e packages/tessera-recipes \
            -e packages/tessera-api \
            -e packages/tessera-rag \
            -e packages/tessera-repo \
            -e packages/tessera-changelog \
            -e packages/tessera-config \
            -e packages/tessera-openapi \
            -e packages/tessera-docs \
            -e packages/tessera-sql \
            -e packages/tessera-todo \
            -e packages/tessera-deps \
            -e packages/tessera-tests \
            -e packages/tessera-links \
            -e packages/tessera-app
```

## Run the whole hub over a project (the app)

```bash
tessera detect --input .              # which packs apply, without running
tessera run --input . --output run    # run applicable packs + build a dashboard
```

`tessera run` detects which packs fit the project (prompt files → prompts, `SKILL.md` → skills, curl files → api, a corpus + queries → rag, source/manifest → repo, a CSV → evals, ...), runs each into `run/<pack>/`, and writes `run/index.html` — a self-contained dashboard (no server, no JS, no external assets) aggregating every pack's reports. Rebuild the dashboard from an existing run with `tessera dashboard --input run`.

## List installed plugins

```bash
tessera plugins
```

Output (two groups, deliberately separate):

```text
CLI Command Plugins (tessera.commands)
  evals

Job Packs (tessera.jobpacks)
  example  0.1.0  ExamplePack
  evals    0.1.0  EvalsPack
```

`example` is a no-op pack shipped in core so the JobPack contract has at least one non-evals implementer.

## Compile an eval pack

```bash
tessera evals compile \
  --input examples/evals/support_logs.csv \
  --task customer_support \
  --output ./out/eval_pack
```

Artifacts written to `./out/eval_pack/`:

```text
dataset.jsonl            canonical EvalRecord rows
golden_candidates.csv    rows needing human review
rubric.yaml              deterministic task-keyed rubric template
coverage_report.md       task breakdown + needs-review count
data_quality_report.md   column detection table + warnings + override hint
```

### Column detection and override

The compiler auto-detects which CSV columns hold the input, expected answer, and context, with a confidence score for each. Detection has five tiers: exact match (0.95), normalized match after stripping common prefix/suffix wrappers (0.95), token match (0.85), substring match (0.70), and a content-based fallback for the input field when header detection fails (0.40). Manual overrides always win at 1.00.

If detection is uncertain or wrong, override:

```bash
tessera evals compile \
  --input data.csv \
  --task rag_qa \
  --input-column customer_question \
  --expected-column approved_answer \
  --context-column policy_text
```

The `data_quality_report.md` always shows the detection table and a column analysis table (inferred type, completeness, length, distinct values) so you can verify the picked columns at a glance.

Sample messy CSVs covering each detection path live under `examples/evals/messy/`:

```bash
tessera evals compile --input examples/evals/messy/compound_prefix.csv --task customer_support --output ./out/cp
tessera evals compile --input examples/evals/messy/wrapper_suffix.csv  --task customer_support --output ./out/ws
tessera evals compile --input examples/evals/messy/unusual_aliases.csv --task rag_qa           --output ./out/ua
tessera evals compile --input examples/evals/messy/cryptic_kb.csv      --task customer_support --output ./out/ck
```

All four compile correctly with no override flags.

### Supported task types

`customer_support`, `rag_qa`, `summarization`, `classification`, `agent_workflow`, `generic`.

Each task type has its own deterministic rubric template (dimensions, must, must-not). Unknown task types fall back to `generic`. LLM-based rubric enrichment is intentionally not in v0.1.

### Export to eval frameworks

A canonical `dataset.jsonl` exports to framework-native interchange files. Tessera emits each target's documented format; it does not import the frameworks.

```bash
tessera evals export --input ./out/eval_pack/dataset.jsonl --target all --output ./out/export
```

| Target | File | Shape |
|---|---|---|
| `deepeval` | `deepeval_goldens.json` | `{goldens: [{input, expected_output, context}]}` |
| `ragas` | `ragas_dataset.jsonl` | `{question, ground_truth, contexts}` per line |
| `openai-evals` | `openai_evals_samples.jsonl` | `{input: [chat messages], ideal}` per line |
| `langsmith` | `langsmith_examples.jsonl` | `{inputs, outputs}` per line |

Use `--target deepeval` (etc.) for a single framework, or `--target all`.

## Compile a prompt catalog

```bash
tessera prompts compile --input examples/prompts/ --output ./out/prompt_pack
```

Each prompt is a frontmatter + body file. Two input shapes are supported:

- `<name>.prompt.md` (single file)
- `<name>/PROMPT.md` (folder, allows attachments like test cases or variants alongside)

Artifacts written:

```text
index.jsonl              canonical PromptCase rows (pydantic-serialized)
index.md                 human-readable catalog
examples.jsonl           inline examples extracted from frontmatter
validation_report.md     issues (missing vars, version errors, name collisions, ...)
coverage_report.md       tag distribution + example coverage + languages
```

Validation rules catch: missing name, non-canonical name, invalid SemVer, missing/short description, empty body, undeclared variables, unused variables, examples missing required variables, and duplicate `name + version` pairs across the catalog.

## Compile a skill catalog

```bash
tessera skills compile --input examples/skills/ --output ./out/skill_pack
```

Each skill is a folder containing a `SKILL.md` (YAML frontmatter + markdown body), optionally with `scripts/`, `references/`, or `examples/` siblings. The compiler inventories every file with a kind classification, extracts runtime dependencies from the body (bash commands, MCP tools, skill-to-skill references), and detects description overlap that could cause silent skill-misfire under an agent.

Artifacts written:

```text
index.jsonl              canonical SkillManifest rows
index.md                 human-readable catalog with file count + size + dep counts
validation_report.md     per-record + cross-record findings
coverage_report.md       tag distribution + file-kind coverage
dependencies_report.md   bash / MCP / skill-to-skill surface + overlap matrix
```

Validation rules catch: missing/non-canonical name, missing/short description, descriptions lacking trigger phrasing, invalid SemVer, empty body, name collisions, and description overlap (token Jaccard > 0.5 warns, > 0.7 errors).

## Compile a recipe pack

```bash
tessera recipes compile --input examples/recipes/ --output ./out/recipe_pack
```

Each recipe is a frontmatter + body file (`<name>.recipe.md` or `<name>/RECIPE.md`) whose frontmatter declares `inputs`, `outputs`, and a list of `steps`. Steps depend on each other via explicit `needs` or via `${steps.X.output}` references in their inputs (both forms are unioned into the dependency graph). The compiler validates the graph (cycles, dangling references, reachability) and computes a topological execution order.

Artifacts written:

```text
index.jsonl              canonical Recipe rows
plans.jsonl              machine execution plan per recipe (topo order, edges, cycle)
index.md                 human-readable catalog
validation_report.md     graph + frontmatter findings
coverage_report.md       step counts, acyclic ratio, tag distribution
execution_plans.md       per-recipe topological order + dependency edges
```

Validation rules catch: cyclic dependencies (with the cycle path), dangling step/input references, self-dependencies, duplicate/missing step ids, unproduced declared outputs, unreachable steps, plus the usual name/version/description checks.

## Compose packs: prompts into evals

Packs compose through artifacts, not imports. A prompts-pack `examples.jsonl` can feed the evals pack directly:

```bash
tessera prompts compile --input examples/prompts/ --output ./out/prompt_pack
tessera evals compile --input ./out/prompt_pack --from-prompts --task customer_support --output ./out/eval_pack
```

The evals pack reads the documented `examples.jsonl` interchange shape (it does not import `tessera-prompts`), maps each prompt example to an `EvalRecord` (input from `rendered_prompt`, expected from `expected`), and stamps `metadata.origin = "prompts"` for provenance. `--input` accepts either the prompt-pack directory or the `examples.jsonl` file directly.

## Compile an API surface map

```bash
tessera api compile --input examples/api/ --output ./out/api_pack
```

Parses `.curl` / `.sh` files of curl commands into canonical `ApiRequest` records. **Secrets are redacted at parse time** — auth headers, `-u` basic-auth, secret query params, and secret-keyed body fields are masked before any value reaches a record, and the raw command is never stored. Artifacts:

```text
index.jsonl              canonical, redacted ApiRequest rows
index.md                 catalog (method, host, path, auth kind, redaction count)
validation_report.md     hygiene findings (insecure scheme, secret-in-URL, no auth, ...)
coverage_report.md       method / host / auth-kind distribution
redactions_report.md     audit trail: every secret masked, with safe previews
```

This pack does not execute requests; live calling/batch/streaming are deferred to a later version. v0.1 is the offline "what is this API surface, and does it leak secrets" pass.

## Run the tests

```bash
.venv/bin/python -m pytest packages/tessera-core/tests \
                           packages/tessera-evals/tests \
                           packages/tessera-prompts/tests \
                           packages/tessera-skills/tests \
                           packages/tessera-recipes/tests \
                           packages/tessera-api/tests \
                           packages/tessera-rag/tests \
                           packages/tessera-repo/tests \
                           packages/tessera-app/tests \
                           packages/tessera-changelog/tests \
                           packages/tessera-config/tests \
                           packages/tessera-openapi/tests \
                           packages/tessera-docs/tests \
                           packages/tessera-sql/tests \
                           packages/tessera-todo/tests \
                           packages/tessera-deps/tests \
                           packages/tessera-tests/tests \
                           packages/tessera-links/tests
```

## Build wheels

```bash
python -m pip install build
python -m build packages/tessera-core
python -m build packages/tessera-evals
python -m build packages/tessera-prompts
python -m build packages/tessera-skills
python -m build packages/tessera-recipes
python -m build packages/tessera-api
python -m build packages/tessera-rag
python -m build packages/tessera-repo
python -m build packages/tessera-app
python -m build packages/tessera-changelog
python -m build packages/tessera-config
python -m build packages/tessera-openapi
python -m build packages/tessera-docs
python -m build packages/tessera-sql
python -m build packages/tessera-todo
python -m build packages/tessera-deps
python -m build packages/tessera-tests
python -m build packages/tessera-links
```
