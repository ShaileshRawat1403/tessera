# tesserakit-links

Check Markdown links for broken file references, dead anchors, and orphaned docs.

`tessera-links` scans Markdown files, resolves every inline link, and flags the ones that point nowhere. External URLs are inventoried but never fetched (no network), keeping the check fast and offline.

## Check

```bash
tessera links check --input . --output ./out/links_pack
```

Artifacts written:

```text
links.jsonl              one Link per inline link (kind, target, broken flag)
index.md                 the link inventory
validation_report.md     broken-link / broken-anchor / orphan findings
coverage_report.md       links by kind (internal / anchor / external / mailto)
broken.md                every broken link + the list of orphan docs
```

## What it checks

- **Internal file links** (`./foo.md`, `../x/y.md`): the target file must exist.
- **Anchors** (`#section`, `foo.md#section`): the heading must exist in the target file (GitHub-style slug).
- **Orphan docs**: Markdown files that no other doc links to (excluding `README.md` / `index.md`).
- **External** (`http(s)://`) and **mailto:** links are inventoried but not validated.

## Findings

- `broken_link` — internal link to a missing file
- `broken_anchor` — link to a heading anchor that does not exist
- `orphan_doc` — a Markdown file linked from nowhere
- `no_links` — nothing found
