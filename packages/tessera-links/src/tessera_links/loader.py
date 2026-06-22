from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_links.scan import (
    discover_md_files,
    extract_links,
    headings_in,
)
from tessera_links.schema import Link


def _classify(href: str) -> str:
    h = href.strip()
    if h.startswith(("http://", "https://")):
        return "external"
    if h.startswith("mailto:"):
        return "mailto"
    if h.startswith("#"):
        return "anchor"
    return "internal"


def load_link_records(input_path: Path, options: dict[str, Any]) -> list[Link]:
    root = input_path if input_path.is_dir() else input_path.parent
    md_files = discover_md_files(root)
    headings_cache: dict[str, set[str]] = {}

    def headings_for(path: Path) -> set[str]:
        key = str(path)
        if key not in headings_cache:
            headings_cache[key] = headings_in(path)
        return headings_cache[key]

    links: list[Link] = []
    referenced_targets: set[str] = set()

    for f in md_files:
        rel = f.relative_to(root).as_posix()
        for lineno, text, href in extract_links(f):
            kind = _classify(href)
            link = Link(source_file=rel, lineno=lineno, text=text, href=href, kind=kind)

            if kind == "anchor":
                anchor = href[1:]
                link.anchor = anchor
                if anchor.lower() not in headings_for(f):
                    link.broken = True
                    link.reason = f"no heading anchor '#{anchor}' in this file"
            elif kind == "internal":
                path_part, _, anchor = href.partition("#")
                link.anchor = anchor
                target = (f.parent / path_part).resolve() if path_part else f.resolve()
                try:
                    target_rel = target.relative_to(root.resolve()).as_posix()
                except ValueError:
                    target_rel = path_part
                link.target_path = target_rel
                if not target.exists():
                    link.broken = True
                    link.reason = f"target file not found: {path_part}"
                else:
                    if target.suffix.lower() in (".md", ".markdown"):
                        referenced_targets.add(target_rel)
                    if anchor and target.suffix.lower() in (".md", ".markdown"):
                        if anchor.lower() not in headings_for(target):
                            link.broken = True
                            link.reason = f"no heading anchor '#{anchor}' in {target_rel}"
            links.append(link)

    # orphan detection: md files referenced by no internal link (excluding entry docs)
    entry_names = {"readme.md", "index.md"}
    orphans: list[str] = []
    for f in md_files:
        rel = f.relative_to(root).as_posix()
        if f.name.lower() in entry_names:
            continue
        if rel not in referenced_targets:
            orphans.append(rel)

    options["_orphans"] = orphans
    options["_md_count"] = len(md_files)
    options["_root"] = str(root)
    return links
