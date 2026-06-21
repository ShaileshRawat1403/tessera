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
