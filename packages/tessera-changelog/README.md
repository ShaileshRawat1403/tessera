# tesserakit-changelog

Turn git history into a structured `CHANGELOG.md` and release notes.

`tessera-changelog` reads commit history (from a git repository, or a portable `commits.jsonl`), parses Conventional Commits, groups changes by type, and emits a changelog, release notes, and quality reports. It reads git metadata only: no project code is executed and no network calls are made.

## Input

- A **git repository** directory → reads `git log --no-merges` (read-only).
- A **`commits.jsonl`** file, or a directory containing one → parses it directly. Each line: `{"hash": "...", "short_hash": "...", "author": "...", "date": "...", "subject": "feat: ...", "body": "..."}`. Only `subject` is required.

## Build a changelog

```bash
tessera changelog build --input . --output ./out/changelog_pack
tessera changelog build --input . --since v0.1.0          # only since a tag
```

Artifacts written:

```text
commits.jsonl            canonical Commit rows (parsed type/scope/breaking)
CHANGELOG.md             grouped by type, with a Breaking Changes section
release_notes.md         prose summary with highlights
validation_report.md     commit-hygiene findings
coverage_report.md       commit-type distribution, % conventional, authors
```

## Conventional Commits

Subjects of the form `type(scope): description` (and `type!: ...` or a
`BREAKING CHANGE:` body trailer for breaking changes) are parsed into a type,
scope, and breaking flag. Recognized types: `feat`, `fix`, `docs`, `refactor`,
`perf`, `test`, `build`, `ci`, `chore`, `style`, `revert`. Anything else is
grouped under `other` and flagged `non_conventional_commit` (informational).

## Validation rules

- `source_error` — not a git repo and no commits.jsonl, or git failed
- `no_commits` — empty range
- `empty_subject`
- `non_conventional_commit` (info)
- `wip_commit` — looks like a WIP/fixup commit that may not belong in a release
- `breaking_change` — surfaced for visibility
