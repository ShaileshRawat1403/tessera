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

## 5. Eval pack v0.1 flow

```text
CSV input
  ↓ load_eval_records()
    detect_column() for input/expected/context (confidence-scored, override-aware)
    deduplicate by input
    flag empty inputs and missing expected answers
  ↓ validate_eval_records()
    turn detection failures + per-row notes into ValidationFinding objects
  ↓ write_eval_artifacts()
    dataset.jsonl            (EvalRecord, pydantic-serialized)
    golden_candidates.csv    (rows needing human review)
    rubric.yaml              (deterministic, task-keyed template)
    coverage_report.md       (task breakdown + needs-review count)
    data_quality_report.md   (column detection table + warnings + override hint)
```

The CLI is a thin wrapper: it builds a `RunContext`, calls `pack.run()`, prints the artifact table and run summary. Nothing in the CLI knows how `dataset.jsonl` is laid out.

Column detection uses four confidence tiers:

```text
1.00  manual override
0.95  exact match (case-insensitive)
0.85  token match (candidate is a token of the header)
0.70  substring match
0.00  no match
```

`data_quality_report.md` is honest about uncertainty: it always shows the detection table with confidence and reason, and emits a recommended-override block whenever any confidence drops below 0.95.

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
