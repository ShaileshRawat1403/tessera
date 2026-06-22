"""Discover env files and env-var references in source code."""

from __future__ import annotations

import re
from pathlib import Path

_IGNORE = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".tox", "target", ".mypy_cache", ".ruff_cache",
}

_EXAMPLE_MARKERS = ("example", "sample", "template", "dist")

_CODE_SUFFIXES = {".py", ".js", ".ts", ".jsx", ".tsx", ".rb", ".go", ".sh", ".java"}

# os.getenv("X") / os.environ["X"] / os.environ.get("X") / getenv("X")
# process.env.X / process.env["X"] / ENV["X"]
_CODE_PATTERNS = [
    re.compile(r"""\bos\.getenv\(\s*['"]([A-Z][A-Z0-9_]*)['"]"""),
    re.compile(r"""\bos\.environ\.get\(\s*['"]([A-Z][A-Z0-9_]*)['"]"""),
    re.compile(r"""\bos\.environ\[\s*['"]([A-Z][A-Z0-9_]*)['"]\s*\]"""),
    re.compile(r"""\bgetenv\(\s*['"]([A-Z][A-Z0-9_]*)['"]"""),
    re.compile(r"""\bprocess\.env\.([A-Z][A-Z0-9_]*)\b"""),
    re.compile(r"""\bprocess\.env\[\s*['"]([A-Z][A-Z0-9_]*)['"]\s*\]"""),
]


def _walk(root: Path):
    for p in root.rglob("*"):
        if any(part in _IGNORE for part in p.relative_to(root).parts):
            continue
        yield p


def is_env_file(name: str) -> bool:
    n = name.lower()
    return n == ".env" or n.startswith(".env.") or n.endswith(".env")


def is_example_file(name: str) -> bool:
    n = name.lower()
    return any(m in n for m in _EXAMPLE_MARKERS)


def find_env_files(root: Path) -> tuple[list[Path], list[Path]]:
    """Return (real_env_files, example_env_files)."""
    real: list[Path] = []
    example: list[Path] = []
    for p in _walk(root):
        if not p.is_file() or not is_env_file(p.name):
            continue
        (example if is_example_file(p.name) else real).append(p)
    return sorted(real), sorted(example)


def find_code_references(root: Path) -> dict[str, list[str]]:
    """Map env-var name -> list of source files that reference it."""
    refs: dict[str, set[str]] = {}
    for p in _walk(root):
        if not p.is_file() or p.suffix.lower() not in _CODE_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = p.relative_to(root).as_posix()
        for pat in _CODE_PATTERNS:
            for m in pat.finditer(text):
                refs.setdefault(m.group(1), set()).add(rel)
    return {k: sorted(v) for k, v in refs.items()}
