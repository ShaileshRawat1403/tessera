# tesserakit-deps

Audit dependency manifests for pinning discipline, duplicates, and conflicts.

`tessera-deps` parses dependency manifests across ecosystems, classifies how tightly each dependency is pinned, and flags supply-chain hygiene issues. It reads manifests only: no installs, no lockfile resolution, no network.

Where `tessera-repo` lists *that* a manifest declares dependencies, `tessera-deps` analyses *how* they are declared.

## Audit

```bash
tessera deps audit --input . --output ./out/deps_pack
```

Supported manifests: `requirements*.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`.

Artifacts written:

```text
dependencies.jsonl       one Dependency per declaration (ecosystem, scope, constraint, pinning)
index.md                 the inventory table
validation_report.md     pinning + duplicate + conflict findings
coverage_report.md       counts by pinning / ecosystem / scope
duplicates.md            dependencies declared in more than one manifest
```

## Pinning classification

- **pinned** — an exact version (`==1.2.3`, npm `1.2.3`, cargo `=1.2.3`, go `v1.2.3`)
- **ranged** — a bounded range (`>=`, `~=`, `^`, `~`, ...)
- **unpinned** — no constraint at all, `*`, or `latest`

## Findings

- `unpinned_dependency` — declared with no version constraint
- `duplicate_dependency` — same name declared in multiple manifests (same constraint)
- `conflicting_constraint` — same name declared with *different* constraints across manifests
- `declared_not_locked` — a manifest dependency is absent from the lockfile (the lock is stale)
- `locked_version_mismatch` — a manifest pins an exact version that disagrees with the lockfile
- `lockfile_missing` — npm/cargo deps are declared but no lockfile exists (builds aren't reproducible)
- `no_dependencies` — nothing found

Lockfile parsing covers `package-lock.json`, `yarn.lock`, `poetry.lock`, and `Cargo.lock`.
