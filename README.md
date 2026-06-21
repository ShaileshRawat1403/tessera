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
| `tessera-evals` | First job pack. Compiles messy CSV data into a canonical eval pack. |

Future packs (RAG, prompts, API tracing, repo mapping) follow the same JobPack contract; they do not require changes to core.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip

pip install -e packages/tessera-core -e packages/tessera-evals
```

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

The compiler auto-detects which CSV columns hold the input, expected answer, and context, with a confidence score for each. If detection is uncertain (or wrong), you can override:

```bash
tessera evals compile \
  --input data.csv \
  --task rag_qa \
  --input-column customer_question \
  --expected-column approved_answer \
  --context-column policy_text
```

Manual overrides always win.

### Supported task types

`customer_support`, `rag_qa`, `summarization`, `classification`, `agent_workflow`, `generic`.

Each task type has its own deterministic rubric template (dimensions, must, must-not). Unknown task types fall back to `generic`. LLM-based rubric enrichment is intentionally not in v0.1.

## Run the tests

```bash
.venv/bin/python -m pytest packages/tessera-core/tests packages/tessera-evals/tests
```

## Build wheels

```bash
python -m pip install build
python -m build packages/tessera-core
python -m build packages/tessera-evals
```
