"""Extract documentable symbols from Python source via the ast module.

Source is parsed, never imported or executed.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tessera_docs.schema import DocSymbol

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".tox", "target", ".mypy_cache", ".ruff_cache",
}


def is_public(name: str) -> bool:
    return not name.startswith("_")


def _is_test_path(rel: Path) -> bool:
    parts = [p.lower() for p in rel.parts]
    if any(p in ("test", "tests", "__tests__") for p in parts[:-1]):
        return True
    n = rel.name.lower()
    return n.startswith("test_") or n.endswith("_test.py")


def discover_py_files(root: Path, include_tests: bool = False) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        if not include_tests and _is_test_path(rel):
            continue
        out.append(p)
    return out


def extract_symbols(root: Path, path: Path) -> tuple[list[DocSymbol], str | None]:
    """Return (symbols, parse_error). Parse error is a string or None."""
    rel = path.relative_to(root).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return [], f"{rel}: {exc}"

    symbols: list[DocSymbol] = []

    # module-level symbol
    mod_doc = ast.get_docstring(tree)
    symbols.append(DocSymbol(
        path=rel, qualname="", kind="module", name=Path(rel).stem, lineno=1,
        is_public=True, has_docstring=mod_doc is not None,
        docstring_len=len(mod_doc or ""),
    ))

    def walk(nodes, prefix: str, inside_class: bool) -> None:
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "method" if inside_class else "function"
                _add(node, kind, prefix)
                # nested functions/classes
                walk(node.body, f"{prefix}{node.name}.", inside_class=False)
            elif isinstance(node, ast.ClassDef):
                _add(node, "class", prefix)
                walk(node.body, f"{prefix}{node.name}.", inside_class=True)

    def _add(node, kind: str, prefix: str) -> None:
        doc = ast.get_docstring(node)
        qual = f"{prefix}{node.name}"
        symbols.append(DocSymbol(
            path=rel, qualname=qual, kind=kind, name=node.name, lineno=node.lineno,
            is_public=is_public(node.name), has_docstring=doc is not None,
            docstring_len=len(doc or ""),
        ))

    walk(tree.body, prefix="", inside_class=False)
    return symbols, None
