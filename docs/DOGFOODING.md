# Dogfooding report

Tessera is validated not only by unit tests but by running the whole hub
(`tessera run`) against real, non-synthetic codebases and reviewing every
finding for accuracy. This page records that pass.

## What was run

| Subject | What it is | Packs that applied |
|---|---|---|
| **Tessera itself** | this 24-package monorepo (real Python source, 24 manifests, docs, git history, a full `examples/` tree) | all 19 applicable |
| **pallets/click** | a widely-used, security-mature Python CLI library (shallow clone) | 10 applicable |

Both were run with `tessera run --input <repo>`, producing the same artifacts
and dashboard a user would get.

## Headline result: no crashes

Across both repos, **every pack completed without raising** — not merely caught
by the orchestrator's fault isolation, but genuinely exception-free on real,
messy input. The orchestrator's per-pack isolation was never needed as a
safety net here; it remains for defense in depth.

## Accuracy spot-checks

- **gha on click** — flagged only click's real gap (`missing_timeout` on jobs)
  and produced **zero false positives on unpinned actions**, because click
  already pins its actions to commit SHAs (it even runs `zizmor`). Tessera's
  security read agreed with a security-conscious project.
- **deps on Tessera** — correctly reported that our own packages are perfectly
  consistent (`rich>=13.7` across all 24) while still surfacing the intentional
  conflicting constraints in the `examples/deps` fixtures.
- **glossary on Tessera** — found genuine terminology drift in our own code
  (`ctx` 655 vs `context` 284; `dir` vs `directory`; `docs`/`doc`/`documentation`).
- **docs on Tessera** — honest docstring-coverage numbers, no false positives.
- **links on Tessera** — correctly found the single real cross-doc link and
  skipped code-fenced examples.

## Precision fixes made as a direct result

Dogfooding surfaced two real false-positive classes, both now fixed:

1. **glossary — single-occurrence minority forms.** A concept was reported as
   "inconsistent" even when the alternate spelling appeared only once (a
   coincidental token). Minority forms must now appear at least twice. On
   Tessera this dropped reported inconsistencies from 30 to 21, removing the
   noise while keeping every real case.

2. **links — orphan docs on non-markdown-linked docsets.** `orphan_doc` fired
   on every page of a Sphinx/mkdocs project, because those navigate via a
   `toctree`/nav rather than inline markdown links. Orphan detection is now
   gated on the project actually using markdown cross-linking. This removed
   **40 false orphan findings** on click (40 → 0) with no loss on projects that
   do cross-link with markdown.

## Status

259 unit tests pass; the two repos above run clean. The heuristic packs
(glossary, links, docs, todo, sql, api) have now been exercised on real input
and tuned for it, not just on the authored fixtures.
