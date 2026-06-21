# tessera-recipes

Compile multi-step workflow recipes into validated, dependency-ordered assets.

`tessera-recipes` reads a directory of recipe files (frontmatter + body), normalizes them into a canonical `Recipe` schema, validates the step dependency graph (cycle detection, dangling references, reachability), computes a topological execution order, and emits a catalog plus machine and human execution plans.

## Input shape

Each recipe is either a single file `<name>.recipe.md` or a folder `<name>/RECIPE.md`. The file is YAML frontmatter followed by a markdown body.

```markdown
---
name: release-notes
description: Build release notes from commits, then summarize and publish.
version: 1.0.0
tags: [git, release]
inputs:
  - name: since_tag
    type: string
    required: true
outputs:
  - name: published_url
steps:
  - id: collect
    uses: changelog-generator
    inputs:
      range: "${inputs.since_tag}..HEAD"
    produces: raw_changelog
  - id: summarize
    needs: [collect]
    inputs:
      text: "${steps.collect.output}"
    produces: summary
  - id: publish
    inputs:
      body: "${steps.summarize.output}"
    produces: published_url
---
Human-readable narrative of the workflow goes here.
```

Step dependencies are the union of explicit `needs` and edges inferred from `${steps.X}` references in `inputs`, so authors can rely on either form.

## Compile a recipe pack

```bash
tessera recipes compile --input examples/recipes/ --output ./out/recipe_pack
```

Artifacts written:

```text
index.jsonl              canonical Recipe rows
plans.jsonl              machine execution plan per recipe (topo order, edges, cycle)
index.md                 human-readable catalog
validation_report.md     graph + frontmatter findings
coverage_report.md       step counts, acyclic ratio, tag distribution
execution_plans.md       per-recipe topological order + dependency edges
```

## Validation rules

Frontmatter / structure:

- `missing_name`, `non_canonical_name`, `invalid_version`, `missing_description`, `short_description`, `no_steps`

Steps and graph:

- `missing_step_id`, `duplicate_step_id`
- `self_dependency` — a step depends on or references itself
- `dangling_needs` — `needs` names a step that does not exist
- `dangling_step_reference` — `${steps.X}` points to a missing step
- `dangling_input_reference` — `${inputs.X}` references an undeclared input
- `cyclic_dependency` — the step graph contains a cycle (reports the cycle path)
- `unproduced_output` — a declared output is not produced by any step
- `unreachable_step` — a step produces nothing and nothing depends on it

Cross-recipe:

- `name_collision` — two recipes share a name
