# SystemSDK Starter

Reusable SDK tools that turn messy AI and engineering workflows into validated, reviewable, export-ready artifacts.

This starter uses a two-layer package model:

- `systemsdk-core`: shared runtime, workspace, artifact writing, plugin loading, validators.
- `systemsdk-evals`: first job pack for compiling messy CSV data into eval-ready assets.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e packages/systemsdk-core -e packages/systemsdk-evals
```

## Try the eval job

```bash
systemsdk init
systemsdk evals compile --input examples/evals/support_logs.csv --task customer_support --output ./out/eval_pack
```

Expected output:

```text
out/eval_pack/
  dataset.jsonl
  golden_candidates.csv
  rubric.yaml
  coverage_report.md
  data_quality_report.md
```

## Build wheels

```bash
python -m pip install build
python -m build packages/systemsdk-core
python -m build packages/systemsdk-evals
```
