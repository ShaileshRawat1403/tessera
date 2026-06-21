---
name: api-docs-check
description: Use this skill when the user wants API documentation validated against an OpenAPI schema. Triggers on "check the API docs", "do the docs match the schema", or "verify docs for endpoint X".
version: 1.1.0
tags: [api, docs, validation]
license: MIT
---

Validate that hand-written API docs agree with the canonical OpenAPI schema.

## What this skill does

For each endpoint documented under `docs/api/`, check that:

- Every path parameter in the doc appears in the schema
- Every required schema field is mentioned in the doc
- The HTTP method matches
- Example payloads parse against the schema

## Helpers

See `references/style_guide.md` for the docs format we follow, and
`examples/sample_check.md` for a worked example.

## Output

A Markdown report grouped by endpoint, with severity per finding:

```bash
diff docs/api/users.md schema/users.yaml
```
