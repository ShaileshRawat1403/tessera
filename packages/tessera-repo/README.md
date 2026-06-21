# tesserakit-repo

Map a repository into a validated structural artifact: a file inventory, a language and layout map, the declared dependency surface, and repo-hygiene signals.

`tessera-repo` walks a repository (ignoring build and vendor directories), classifies every file by language and kind, detects and parses dependency manifests, and emits a structural map plus reports. It reads code; it does not run it, and it makes no network calls.

## Scope (v0.1)

Pure structural analysis. No code execution, no imports of the target repo, no network. The output is an offline, reviewable map of what a repository contains.

## Map a repository

```bash
tessera repo map --input . --output ./out/repo_pack
```

Artifacts written:

```text
files.jsonl              one RepoFile per file (path, language, kind, loc, bytes)
repo_map.json            aggregate map (languages, top-level layout, manifests, signals)
index.md                 human-readable map
validation_report.md     hygiene findings
coverage_report.md       files by kind + test-to-source ratio
dependencies_report.md   declared dependencies across all manifests
```

## What it detects

- **Languages** by extension (Python, JS/TS, Go, Rust, Java, ... plus config/docs/data).
- **File kinds**: `source`, `test`, `config`, `docs`, `build`, `data`, `asset`, `other`.
- **Dependency manifests**: `pyproject.toml`, `package.json`, `requirements.txt`, `Cargo.toml`, `go.mod` — parsed best-effort for declared dependency names.
- **Hygiene signals**: README, LICENSE, tests, CI config, .gitignore present.

## Validation rules

- `empty_repo` — nothing found after ignoring build/vendor dirs
- `missing_readme`, `missing_license`
- `no_tests_detected`
- `no_dependency_manifest`, `no_ci_config`
- `large_source_file` — a source file over 800 lines of code
