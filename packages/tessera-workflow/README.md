# tesserakit-workflow

Validate **Workflow Pack profile** definitions: the governance schema that sits on top of the Tessera JobPack contract.

A Workflow Pack defines a governed multi-step workflow as a YAML file. This pack validates it:

- all steps have declared outputs (traceable)
- review gates reference real steps
- a recursion fence is declared
- evidence policy has hash-invariant steps (TOCTOU guard)
- no step references an undeclared adapter

## Quickstart

```bash
tessera workflow validate --input examples/workflow/valid_codeops.workflow.yaml --output out/
open out/governance_report.md
```

## What it checks

| Code | Severity | Description |
|------|----------|-------------|
| `no_steps` | error | Workflow defines no steps |
| `review_gate_unknown_step` | error | Gate references a step that does not exist |
| `invalid_promotion_rule` | error | `promotion_rule` is not a known value |
| `capability_envelope_unknown_step` | error | Envelope references a step that does not exist |
| `missing_recursion_fence` | warning | No recursion fence defined (kernel-path mutation risk) |
| `promotion_without_review` | warning | `promotion_rule: after_review` but no gates defined |
| `undefined_adapter` | warning | Step uses adapter not listed in `required_adapters` |
| `missing_evidence_hash_invariant` | warning | No hash-invariant steps (TOCTOU risk) |
| `step_undefined_input` | warning | Step input not produced by any earlier step |
| `step_missing_outputs` | info | Step has no outputs (untraceable) |

## Workflow Pack schema

```yaml
name: my.workflow
version: "0.1"
steps:
  - name: step_one
    adapter: tessera_repo
    outputs: [repo_map.jsonl]
  - name: step_two
    adapter: codegen
    inputs: [repo_map.jsonl]
    outputs: [patch.diff, patch_hash.txt]

required_adapters: [tessera_repo, codegen]
review_gates:
  - after_step: step_two
    label: human_review
evidence_policy:
  hash_invariant_steps: [step_two]
recursion_fence:
  protected_paths: [kernel/]
promotion_rule: after_review
```
