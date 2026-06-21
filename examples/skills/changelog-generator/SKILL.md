---
name: changelog-generator
description: Use this skill when the user asks for a changelog, release notes, or a summary of what shipped recently. Triggers on phrases like "make a changelog", "what shipped this week", "release notes for v1.2", or "what changed since last release".
version: 1.0.0
tags: [git, release, changelog]
---

Generate a changelog from recent git commits.

## How to invoke

```bash
git log --oneline --no-merges v1.0.0..HEAD
```

Then group commits by type (feat, fix, docs, refactor) and produce a Markdown
section per type. Skip commits that only touch generated files.

## Output shape

A single Markdown block, headed by the version range and date, grouped by
commit type. Cite each commit's short SHA at the end of the line.
