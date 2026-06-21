# SystemSDK Architecture

```text
Messy source data
  ↓
Input adapter
  ↓
Normalizer
  ↓
Job-specific mapper
  ↓
Validator / quality gates
  ↓
Human review artifact
  ↓
Framework-ready export
```

## Package model

```text
systemsdk-core
  workspace
  run context
  validators
  artifact writers
  plugin loader
  CLI shell

systemsdk-evals
  dataset profiler
  canonical eval schema
  golden candidate builder
  rubric generator
  eval pack exporter
```

## Principle

The core package should not know eval-specific logic.
The eval package should use the core runtime and register its own CLI commands.
