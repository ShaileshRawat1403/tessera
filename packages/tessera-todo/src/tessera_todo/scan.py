"""Scan source files for code markers (TODO/FIXME/...)."""

from __future__ import annotations

import re
from pathlib import Path

from tessera_todo.schema import TodoItem

_IGNORE = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".tox", "target", ".mypy_cache", ".ruff_cache",
}

_SCAN_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb",
    ".php", ".c", ".h", ".cpp", ".hpp", ".cs", ".swift", ".scala", ".sh",
    ".sql", ".md", ".rst", ".yaml", ".yml", ".toml", ".txt", ".cfg", ".ini",
}

HIGH = {"FIXME", "HACK", "XXX", "BUG"}
LOW = {"NOTE", "OPTIMIZE", "DEPRECATED"}
MARKERS = HIGH | LOW | {"TODO", "REFACTOR"}

# MARKER, optional (owner), optional :, then text
_MARKER_RE = re.compile(
    r"\b(TODO|FIXME|HACK|XXX|BUG|NOTE|OPTIMIZE|REFACTOR|DEPRECATED)\b"
    r"(?:\(([^)]*)\))?\s*:?\s*(.*)$"
)


def _priority(marker: str) -> str:
    if marker in HIGH:
        return "high"
    if marker in LOW:
        return "low"
    return "normal"


def _walk(root: Path):
    for p in root.rglob("*"):
        if any(part in _IGNORE for part in p.relative_to(root).parts):
            continue
        yield p


def scan_todos(root: Path) -> tuple[list[TodoItem], int]:
    """Return (items, files_scanned)."""
    items: list[TodoItem] = []
    files = 0
    for p in _walk(root):
        if not p.is_file() or p.suffix.lower() not in _SCAN_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        files += 1
        rel = p.relative_to(root).as_posix()
        for i, line in enumerate(text.splitlines(), start=1):
            m = _MARKER_RE.search(line)
            if not m:
                continue
            marker = m.group(1).upper()
            owner = (m.group(2) or "").strip()
            body = (m.group(3) or "").strip()
            items.append(
                TodoItem(
                    marker=marker, priority=_priority(marker), owner=owner,
                    text=body[:200], file=rel, lineno=i,
                )
            )
    return items, files
