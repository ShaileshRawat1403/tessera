from __future__ import annotations

from pathlib import Path

# Directories never descended into.
IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "dist", "build", ".tox", ".eggs", "target", ".next", ".cache",
    ".idea", ".vscode", "coverage", "htmlcov",
}

_EXT_LANG = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".rb": "Ruby", ".php": "PHP", ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".cs": "C#",
    ".swift": "Swift", ".scala": "Scala", ".sh": "Shell", ".bash": "Shell",
    ".md": "Markdown", ".markdown": "Markdown", ".rst": "reStructuredText",
    ".yaml": "YAML", ".yml": "YAML", ".json": "JSON", ".toml": "TOML",
    ".ini": "INI", ".cfg": "INI", ".xml": "XML", ".html": "HTML",
    ".css": "CSS", ".scss": "CSS", ".sql": "SQL", ".csv": "CSV",
    ".jsonl": "JSONL", ".txt": "Text",
}

_SOURCE_LANGS = {
    "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "Kotlin",
    "Ruby", "PHP", "C", "C++", "C#", "Swift", "Scala", "Shell", "SQL",
}

_CONFIG_EXTS = {".toml", ".yaml", ".yml", ".ini", ".cfg", ".json", ".xml"}
_DATA_EXTS = {".csv", ".jsonl", ".tsv", ".parquet"}
_ASSET_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".woff", ".woff2"}
_DOC_EXTS = {".md", ".markdown", ".rst", ".txt"}

_BUILD_NAMES = {
    "pyproject.toml", "setup.py", "setup.cfg", "package.json", "cargo.toml",
    "go.mod", "makefile", "dockerfile", "requirements.txt", "pipfile",
    "poetry.lock", "package-lock.json", "yarn.lock", "cargo.lock", "go.sum",
}


def language_for(path: Path) -> str:
    return _EXT_LANG.get(path.suffix.lower(), "unknown")


def kind_for(rel: Path) -> str:
    name = rel.name.lower()
    parts = [p.lower() for p in rel.parts]
    suffix = rel.suffix.lower()

    if name in _BUILD_NAMES or name.endswith(".lock"):
        return "build"
    if any(p in ("test", "tests", "__tests__", "spec") for p in parts[:-1]):
        return "test"
    if name.startswith("test_") or name.endswith("_test.py") or ".test." in name or ".spec." in name:
        return "test"
    if suffix in _DOC_EXTS or "docs" in parts[:-1]:
        return "docs"
    if suffix in _ASSET_EXTS:
        return "asset"
    if suffix in _DATA_EXTS:
        return "data"
    if suffix in _CONFIG_EXTS or name.startswith("."):
        return "config"
    if language_for(rel) in _SOURCE_LANGS:
        return "source"
    return "other"
