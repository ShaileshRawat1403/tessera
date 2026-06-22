from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_docs.scan import discover_py_files, extract_symbols
from tessera_docs.schema import DocSymbol


def load_docs_records(input_path: Path, options: dict[str, Any]) -> list[DocSymbol]:
    """Extract documentable symbols from every (non-test) Python file."""
    root = input_path if input_path.is_dir() else input_path.parent
    include_tests = bool(options.get("include_tests", False))

    symbols: list[DocSymbol] = []
    parse_errors: list[str] = []
    files = discover_py_files(root, include_tests=include_tests)
    for f in files:
        syms, err = extract_symbols(root, f)
        symbols.extend(syms)
        if err:
            parse_errors.append(err)

    options["_parse_errors"] = parse_errors
    options["_file_count"] = len(files)
    options["_root"] = str(root)
    return symbols
