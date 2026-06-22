"""Discover tests and their hygiene facts via ast (no imports, no execution)."""

from __future__ import annotations

import ast
from pathlib import Path

from tessera_tests.schema import TestCase

_IGNORE = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".tox", "target",
}


def is_test_file(rel: Path) -> bool:
    n = rel.name
    if not n.endswith(".py"):
        return False
    if n.startswith("test_") or n.endswith("_test.py"):
        return True
    parts = [p.lower() for p in rel.parts[:-1]]
    return any(p in ("test", "tests") for p in parts) and n != "__init__.py"


def discover_test_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root)
        if any(part in _IGNORE for part in rel.parts):
            continue
        if is_test_file(rel):
            out.append(p)
    return out


def _decorator_str(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        return _decorator_str(node.func)
    if isinstance(node, ast.Attribute):
        return f"{_decorator_str(node.value)}.{node.attr}"
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _count_assertions(fn: ast.AST) -> int:
    count = 0
    for node in ast.walk(fn):
        if isinstance(node, ast.Assert):
            count += 1
        elif isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute):
                attr = target.attr.lower()
                if attr.startswith("assert"):
                    count += 1
                elif attr in ("raises", "warns", "deprecated_call"):
                    count += 1
    return count


def _make_case(fn: ast.AST, rel: str, kind: str, prefix: str) -> TestCase:
    decorators = [d for d in (_decorator_str(x) for x in fn.decorator_list) if d]
    lowered = " ".join(decorators).lower()
    n = _count_assertions(fn)
    return TestCase(
        name=fn.name,
        qualname=f"{prefix}{fn.name}",
        kind=kind,
        file=rel,
        lineno=fn.lineno,
        decorators=decorators,
        is_skipped="skip" in lowered,
        is_xfail="xfail" in lowered,
        is_parametrized="parametrize" in lowered,
        assertion_count=n,
        has_assert=n > 0,
    )


def extract_tests(root: Path, path: Path) -> tuple[list[TestCase], str | None]:
    rel = path.relative_to(root).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return [], f"{rel}: {exc}"

    cases: list[TestCase] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            cases.append(_make_case(node, rel, "function", ""))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith("test"):
                    cases.append(_make_case(sub, rel, "method", f"{node.name}."))
    return cases, None
