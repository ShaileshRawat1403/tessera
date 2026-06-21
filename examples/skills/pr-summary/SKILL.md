---
name: pr-summary
description: Use this skill when the user asks for a pull-request summary, a PR description, or a one-paragraph explanation of a diff. Triggers on "summarize this PR", "write a PR description", or "what does this diff do".
version: 0.2.0
tags: [git, review]
---

Summarize a pull request diff in three sections.

## Sections

1. **What changed** in one sentence at the top.
2. **Why it changed** in one or two bullet points (cite the issue or motivation
   if available in the diff or commits).
3. **Test plan** as a short checklist of what a reviewer should verify.

## Inputs

```bash
git diff main...HEAD
```

Keep the output under 200 words unless the user asks for more depth.
