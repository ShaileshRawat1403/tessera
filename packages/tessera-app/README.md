# tesserakit-app

The Tessera app: run the whole hub over a project and get one browsable dashboard.

`tessera-app` is the unifying surface over the job packs. It detects which packs apply to a project, runs them, and renders all their artifacts into a single self-contained HTML dashboard. No server, no build step, no extra dependencies.

It is a **CLI-only plugin**: it registers commands under `tessera.commands` and orchestrates JobPacks, but is not itself a JobPack. (This is the first real use of the deliberate split between the `tessera.commands` and `tessera.jobpacks` entry-point groups.)

## Commands

```bash
tessera detect --input .              # show which packs apply, without running
tessera run --input . --output run    # run applicable packs + build dashboard
tessera dashboard --input run         # (re)build the HTML dashboard from a run
```

## What `run` does

1. **Detects** applicable packs by inspecting the project:
   - `.prompt.md` / `PROMPT.md` → prompts
   - `SKILL.md` → skills
   - `.recipe.md` / `RECIPE.md` → recipes
   - `.curl` / curl `.sh` → api
   - `corpus/` + a `queries.*` file → rag
   - any `.csv` → evals (task `generic`)
   - source files or a dependency manifest → repo
2. **Runs** each applicable pack into `output/<pack>/`, continuing past any pack that fails.
3. **Writes** `run_manifest.json` summarizing record/finding counts and artifacts.
4. **Builds** `output/index.html`: a dashboard with headline cards and every pack's reports, rendered from Markdown to HTML in the browser-ready file.

## Notes

- The orchestrator never raises on a single pack's failure; it records the error and moves on, so one bad input does not sink the whole run.
- The dashboard is fully self-contained (inline CSS, no JS, no external assets) so it can be committed, emailed, or served as a static file.
- For full control over a single pack (e.g. a specific eval task type or column overrides), use that pack's own command (`tessera evals compile ...`).
