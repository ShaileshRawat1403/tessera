# tesserakit-gha

Lint GitHub Actions workflows for security and hygiene.

`tessera-gha` parses `.github/workflows/*.yml`, inventories jobs/steps/actions, and flags the workflow mistakes that lead to supply-chain and injection incidents. It reads YAML only; it never runs a workflow.

## Lint

```bash
tessera gha lint --input . --output ./out/gha_pack
```

Point it at a repo root (it finds `.github/workflows/`), a workflows directory, or a single workflow file.

Artifacts written:

```text
items.jsonl              one WorkflowItem per step (uses/run, pin status, injection flag)
workflows.jsonl          per-workflow facts (triggers, jobs, permissions/timeout gaps)
index.md                 workflow + action inventory
validation_report.md     security + hygiene findings
coverage_report.md       actions used, run vs uses counts
```

## Findings

- `pull_request_target_checkout_rce` (error) — a privileged trigger (`pull_request_target`/`workflow_run`) **and** a checkout of PR-controlled code (`ref: ${{ github.event.pull_request.head.sha }}` etc.); the classic CI remote-code-execution combo
- `script_injection_risk` (error) — a `run:` script interpolates an untrusted `github.event.*` field (title/body/branch); use an intermediate `env:` var
- `unpinned_action` (warning) — a third-party action isn't pinned to a commit SHA (tags are mutable)
- `persist_credentials` (warning) — a checkout keeps the `GITHUB_TOKEN` on disk (`persist-credentials` not disabled)
- `write_all_permissions` (warning) — `permissions: write-all` or broadly-write scopes
- `risky_trigger` (warning) — `pull_request_target` / `workflow_run` run with secrets on untrusted input
- `missing_permissions` (info) — no explicit `permissions:`; jobs get broad default scopes
- `missing_timeout` (info) — a job has no `timeout-minutes`
- `parse_error`, `no_workflows`
