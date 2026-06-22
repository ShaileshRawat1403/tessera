"""Find markdown files, extract links, and collect heading anchors."""

from __future__ import annotations

import re
from pathlib import Path

_IGNORE = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".tox", "target",
}
_MD_SUFFIXES = {".md", ".markdown"}

# inline links: [text](href)   — href may carry a "title" we discard
_LINK_RE = re.compile(r"\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
_SLUG_STRIP = re.compile(r"[^a-z0-9\s-]")


def slugify(heading: str) -> str:
    """GitHub-style heading slug."""
    s = heading.strip().lower()
    s = _SLUG_STRIP.sub("", s)
    s = re.sub(r"\s+", "-", s)
    return s


def discover_md_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if any(part in _IGNORE for part in p.relative_to(root).parts):
            continue
        if p.is_file() and p.suffix.lower() in _MD_SUFFIXES:
            out.append(p)
    return out


def headings_in(path: Path) -> set[str]:
    slugs: set[str] = set()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return slugs
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(line)
        if m:
            slugs.add(slugify(m.group(2)))
    return slugs


def extract_links(path: Path) -> list[tuple[int, str, str]]:
    """Return (lineno, text, href) for each inline link, skipping code fences."""
    out: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return out
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in _LINK_RE.finditer(line):
            out.append((i, m.group(1), m.group(2)))
    return out
