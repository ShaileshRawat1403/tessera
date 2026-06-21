# tessera-skills

Validate and catalog SKILL.md skill collections in the Anthropic Skills convention.

`tessera-skills` reads a directory of skills (each in its own folder, with a `SKILL.md` plus supporting files), normalizes them into a canonical `SkillManifest` schema, validates them, extracts runtime dependencies, and emits a catalog plus reports.

## Input shape

Each skill is a folder containing a `SKILL.md`. Other files alongside (scripts, references, examples) are inventoried automatically.

```text
skills/
  changelog-generator/
    SKILL.md
    scripts/extract_commits.py
  pr-summary/
    SKILL.md
  api-docs-check/
    SKILL.md
    references/style_guide.md
    examples/sample_check.md
```

`SKILL.md` is YAML frontmatter followed by a markdown body:

```markdown
---
name: changelog-generator
description: Use this skill when the user asks for a changelog, release notes, or a summary of recent commits. Triggers on phrases like "make a changelog" or "what shipped this week".
version: 1.0.0
tags: [git, release]
---

Generate a changelog from recent git commits. ...
```

## Compile a skill catalog

```bash
tessera skills compile --input examples/skills/ --output ./out/skill_pack
```

Artifacts written:

```text
index.jsonl              canonical SkillManifest rows
index.md                 human-readable catalog
validation_report.md     correctness findings
coverage_report.md       tag distribution + completeness stats
dependencies_report.md   bash / MCP / skill-to-skill dependency surface + overlap report
```

## Validation rules

Per-record:

- `missing_name`, `non_canonical_name`
- `missing_description`, `short_description`, `description_lacks_triggers`
- `invalid_version`, `empty_body`

Cross-record:

- `name_collision` — two skills share the same `name`
- `description_overlap_warning` — token-similarity > 0.5
- `description_overlap_error` — token-similarity > 0.7 (likely silent misfire under an agent)

## Dependency extraction

The body of each `SKILL.md` is scanned for runtime dependencies that future tooling can verify:

- Bash commands inside ` ```bash ` fences
- MCP tool references matching `mcp__*`
- Other skill references matching `/<skill-slug>`

The extracted lists appear per skill in the index and are aggregated in `dependencies_report.md`.
