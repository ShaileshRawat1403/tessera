# tessera-prompts

Compile messy prompt collections into validated, reviewable, reusable assets.

`tessera-prompts` is a Tessera job pack. It reads a directory of prompt files (frontmatter + body), normalizes them into a canonical `PromptCase` schema, validates them, and emits a catalog plus reports.

## Input shape

Each prompt is either:

- A single file: `<name>.prompt.md`
- A directory: `<name>/PROMPT.md` (optionally with supporting files alongside)

Each file is YAML frontmatter followed by the prompt body.

```markdown
---
name: refund_window
description: Explain the refund eligibility window to a customer.
version: 1.0.0
lang: en
tags: [customer-support, billing]
model_hints:
  temperature: 0.2
  max_tokens: 250
variables:
  - name: customer_name
    type: string
    required: true
  - name: days_since_purchase
    type: number
    required: true
    description: Days between purchase and refund request.
examples:
  - input:
      customer_name: Maya
      days_since_purchase: 18
    expected: Maya, your purchase is within the 30 day refund window...
---
Hi {{customer_name}}, thanks for reaching out about a refund.

Your purchase was {{days_since_purchase}} days ago. Our standard refund window
is 30 days. Here is what that means for your request: ...
```

## Compile a prompt catalog

```bash
tessera prompts compile \
  --input examples/prompts/ \
  --output ./out/prompt_pack
```

Artifacts written:

```text
index.jsonl              canonical PromptCase rows (one per line)
index.md                 human-readable catalog
examples.jsonl           inline examples extracted from frontmatter
validation_report.md     issues found (missing variables, version errors, name collisions, etc.)
coverage_report.md       tag distribution + example coverage + language breakdown
```

## Validation rules

- `missing_name` — frontmatter has no `name`
- `non_canonical_name` — name is not kebab-case or snake-case
- `name_collision` — two prompts share the same `name` (or `name + version`)
- `invalid_version` — version is not SemVer
- `missing_description` — no description in frontmatter
- `short_description` — description is under 10 characters
- `undeclared_variable` — body uses `{{x}}` but `x` is not declared in `variables`
- `unused_variable` — `x` is declared but never used in body
- `example_missing_required_variable` — example input does not supply all required variables
