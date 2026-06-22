# tesserakit-license

Detect and classify a project's license, offline.

`tessera-license` reads `LICENSE` files and the `license` field of manifests, identifies the license by content signature, classifies it (permissive / weak-copyleft / copyleft / public-domain), and flags hygiene issues. No network and no per-dependency registry lookups: it inspects what is declared in the repo.

## Audit

```bash
tessera license audit --input . --output ./out/license_pack
```

Detected sources:

- `LICENSE` / `LICENCE` / `COPYING` files (identified from their text)
- `pyproject.toml` `[project].license`
- `package.json` `license`
- `Cargo.toml` `[package].license`

Recognized ids include MIT, Apache-2.0, BSD-2/3-Clause, ISC, MPL-2.0, (L)GPL-2.0/3.0, AGPL-3.0, Unlicense, CC0-1.0.

Artifacts written:

```text
licenses.jsonl           one LicenseFinding per declaration (id, category, evidence)
index.md                 the license inventory
validation_report.md     hygiene findings
coverage_report.md       counts by category and license id
```

## Findings

- `no_license` — no LICENSE file or declared license found
- `missing_license_file` — a manifest declares a license but there is no LICENSE file
- `copyleft_license` — a copyleft license (GPL/AGPL) needs obligation review
- `license_mismatch` — different licenses declared in different places
- `unrecognized_license` — the license text/value could not be identified
